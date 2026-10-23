"""Windows desktop host for the shared backend and browser dashboard."""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import logging
import queue
import threading
import webbrowser

from .bootstrap import start_services
from .config import APP_VERSION, LOG_PATH, MANAGEMENT_URL
from .diagnostics import log_event


@contextmanager
def single_instance(name: str = 'Local\\Sweety.Portable'):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.CreateMutexW(None, False, name)
    error = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error)
    try:
        yield error != 183  # ERROR_ALREADY_EXISTS
    finally:
        kernel.CloseHandle(handle)


def run_window(*, factory=start_services, on_ready=None, open_browser=True):
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title(f'Sweety {APP_VERSION} — Windows Test')
    root.geometry('460x240')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Sweety', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
    status = tk.StringVar(value='正在啟動 / Starting…')
    ttk.Label(frame, textvariable=status, wraplength=420).pack(anchor='w', pady=12)
    ttk.Label(frame, text='關閉此視窗會停止服務；關閉瀏覽器仍可繼續運作。',
              wraplength=420).pack(anchor='w', pady=(0, 12))
    dashboard = ttk.Button(frame, text='開啟管理介面 / Open dashboard',
                           command=lambda: webbrowser.open(MANAGEMENT_URL), state='disabled')
    dashboard.pack(side='left')
    events = queue.Queue()
    services = None
    busy = True
    closing = False
    failure = None

    def start():
        try:
            events.put(('ready', factory()))
        except Exception as exc:
            log_event(logging.getLogger('sweety.windows'), 'startup_failed', error=type(exc).__name__, exc_info=True)
            events.put(('error', exc))

    def stop():
        try:
            if services is not None:
                services.stop()
        except Exception as exc:
            log_event(logging.getLogger('sweety.windows'), 'shutdown_failed', error=type(exc).__name__, exc_info=True)
        finally:
            events.put(('stopped', None))

    def close():
        nonlocal closing
        if closing:
            return
        closing = True
        dashboard.configure(state='disabled')
        status.set('正在結束 / Stopping…')
        if not busy:
            threading.Thread(target=stop, daemon=True).start()

    def poll():
        nonlocal services, busy, failure
        try:
            kind, value = events.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        if kind == 'stopped':
            root.destroy()
            return
        busy = False
        if kind == 'error':
            failure = value
            status.set(f'啟動失敗 / Startup failed: {value}\n日誌: {LOG_PATH}')
            if closing or on_ready is not None:
                root.destroy()
                return
        else:
            services = value
            if closing:
                threading.Thread(target=stop, daemon=True).start()
            else:
                status.set('服務執行中 / Running — ' + MANAGEMENT_URL)
                dashboard.configure(state='normal')
                if open_browser:
                    webbrowser.open(MANAGEMENT_URL)
                if on_ready is not None:
                    try:
                        on_ready(services, root)
                    except Exception as exc:
                        failure = exc
                    finally:
                        close()
        root.after(100, poll)

    ttk.Button(frame, text='結束 / Quit', command=close).pack(side='right')
    root.protocol('WM_DELETE_WINDOW', close)
    threading.Thread(target=start, name='SweetyStartup', daemon=True).start()
    root.after(100, poll)
    try:
        root.mainloop()
    finally:
        if services is not None:
            services.stop()
    if failure is not None:
        raise failure


def main():
    with single_instance() as acquired:
        if not acquired:
            webbrowser.open(MANAGEMENT_URL)
            return
        run_window()
