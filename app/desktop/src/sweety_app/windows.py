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
from .config import APP_VERSION, LOG_PATH, LOGO_PATH, MANAGEMENT_URL, PANEL_BACKGROUND_PATH, preferred_locale
from .diagnostics import log_event
from .panel_text import ai_timeout_alert_copy, panel_ui_copy, status_text


class WindowsPanel:
    """The Mac panel's artwork, layout and controls on a native Tk canvas."""

    def __init__(self, root, *, toggle, manage, quit):
        import tkinter as tk
        from PIL import Image, ImageDraw, ImageEnhance, ImageTk

        self.root = root
        root.title('Sweety')
        root.geometry('500x500')
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=500, height=500, highlightthickness=0,
                                background='#050a16')
        self.canvas.pack(fill='both', expand=True)
        with Image.open(PANEL_BACKGROUND_PATH) as source:
            background = source.convert('RGB').resize((500, 500), Image.Resampling.LANCZOS)
        for box in ((0, 0, 500, 192), (0, 316, 500, 500)):
            background.paste(ImageEnhance.Brightness(background.crop(box)).enhance(0.52), box)
        self.background = ImageTk.PhotoImage(background, master=root)
        self.canvas.create_image(0, 0, image=self.background, anchor='nw')
        with Image.open(LOGO_PATH) as source:
            self.logo = ImageTk.PhotoImage(source.convert('RGBA').resize((48, 48),
                Image.Resampling.LANCZOS), master=root)
        root.iconphoto(True, self.logo)
        self.canvas.create_image(24, 32, image=self.logo, anchor='nw')
        self._text(84, 36, 'Sweety', 19, bold=True)
        self._text(84, 64, 'Scam Insecticide', 12)
        self._text(441, 52, f'v{APP_VERSION}', 11, bold=True, anchor='center')
        self.selected = self._text(32, 108, '', 13)
        self.count = self._text(32, 132, '0', 42, bold=True)
        self.status = self._text(32, 360, '正在啟動 / Starting…', 13, width=436)
        self.warning_box = self.canvas.create_rectangle(32, 310, 468, 354,
            fill='#3b2c16', outline='#cf8b32', state='hidden')
        self.warning = self._text(44, 316, '', 12, width=412, fill='#ffcf87')
        self.buttons = {}
        self.icons = {}
        # Draw icons as images so Windows font coverage cannot hide the symbols.
        for name in ('play', 'stop', 'manage', 'quit'):
            icon = Image.new('RGBA', (64, 64))
            draw = ImageDraw.Draw(icon)
            if name == 'play':
                draw.polygon([(18, 10), (54, 32), (18, 54)], fill='white')
            elif name == 'stop':
                draw.rounded_rectangle((12, 12, 52, 52), radius=3, fill='white')
            elif name == 'manage':
                draw.ellipse((6, 6, 58, 58), outline='white', width=5)
                draw.polygon([(44, 18), (36, 36), (18, 44), (26, 26)], fill='white')
            else:
                draw.arc((8, 8, 56, 56), 310, 590, fill='white', width=6)
                draw.line((32, 3, 32, 31), fill='white', width=6)
            self.icons[name] = ImageTk.PhotoImage(icon.resize((16, 16), Image.Resampling.LANCZOS), master=root)
        for name, x, width, command in (
            ('toggle', 32, 138, toggle), ('manage', 180, 138, manage),
            ('quit', 328, 140, quit),
        ):
            color = '#0084ff' if name == 'toggle' else '#020509'
            # Rounded surround with a real keyboard-accessible native button.
            points = (x+6, 428, x+width-6, 428, x+width, 428, x+width, 434,
                      x+width, 466, x+width, 472, x+width-6, 472, x+6, 472,
                      x, 472, x, 466, x, 434, x, 428)
            shape = self.canvas.create_polygon(points, smooth=True, fill=color, outline='')
            button = tk.Button(self.canvas, command=command, font=('Microsoft JhengHei UI', -14, 'bold'),
                bg=color, fg='white', activebackground=color, activeforeground='white',
                disabledforeground='#9bacc1', borderwidth=0, relief='flat',
                highlightthickness=0, cursor='hand2', takefocus=True)
            button.configure(image=self.icons['play' if name == 'toggle' else name],
                             compound='left', padx=4)
            button.place(x=x+5, y=432, width=width-10, height=36)
            self.buttons[name] = (button, shape)
        root.bind('<Return>', lambda event: self.buttons['toggle'][0].invoke())
        self.set_locale(preferred_locale())
        self.set_status('正在啟動…' if self.locale == 'zh-TW' else 'Starting…')
        self.set_ready(False)

    def _text(self, x, y, text, size, *, bold=False, **kwargs):
        return self.canvas.create_text(x, y, text=text, anchor=kwargs.pop('anchor', 'nw'),
            fill=kwargs.pop('fill', 'white'),
            font=('Microsoft JhengHei UI', -size, 'bold' if bold else 'normal'), **kwargs)

    def set_locale(self, locale):
        self.locale = locale
        self.copy = panel_ui_copy(locale)
        for button, _shape in self.buttons.values():
            button.configure(font=('Microsoft JhengHei UI', -14 if locale == 'zh-TW' else -12, 'bold'))
        self.canvas.itemconfigure(self.selected, text=self.copy['selected_targets'])
        self.buttons['manage'][0].configure(text=' ' + ('Dashboard' if locale == 'en' else self.copy['open_management']))
        self.buttons['quit'][0].configure(text=' ' + self.copy['quit_app'])
        self.buttons['toggle'][0].configure(text=' ' + self.copy['start'])
        self.canvas.itemconfigure(self.warning, text=ai_timeout_alert_copy(locale))

    def set_ready(self, ready):
        for name in ('toggle', 'manage'):
            self.buttons[name][0].configure(state='normal' if ready else 'disabled')

    def set_status(self, text):
        self.canvas.itemconfigure(self.status, text=text)

    def refresh(self, snapshot):
        enabled = bool(snapshot.get('enabled'))
        self.canvas.itemconfigure(self.count, text=str(snapshot.get('selectedTargetCount', 0)))
        self.set_status(status_text(self.locale, snapshot))
        button, shape = self.buttons['toggle']
        color = '#ff453a' if enabled else '#0084ff'
        button.configure(text=' ' + (self.copy['stop'] if enabled else self.copy['start']),
                         image=self.icons['stop' if enabled else 'play'],
                         bg=color, activebackground=color)
        self.canvas.itemconfigure(shape, fill=color)
        state = 'normal' if snapshot.get('aiTimeoutAlert') else 'hidden'
        self.canvas.itemconfigure(self.warning_box, state=state)
        self.canvas.itemconfigure(self.warning, state=state)


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

    root = tk.Tk()
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
        panel.set_ready(False)
        panel.set_status('正在結束…' if panel.locale == 'zh-TW' else 'Stopping…')
        if not busy:
            threading.Thread(target=stop, daemon=True).start()

    def poll():
        nonlocal services, busy, failure
        try:
            kind, value = events.get_nowait()
        except queue.Empty:
            if services is not None and not busy and not closing:
                panel.refresh(services.monitor.snapshot())
            root.after(100, poll)
            return
        if kind == 'stopped':
            root.destroy()
            return
        busy = False
        if kind == 'changed':
            if closing:
                threading.Thread(target=stop, daemon=True).start()
            else:
                panel.refresh(services.monitor.snapshot())
                panel.set_ready(True)
            root.after(100, poll)
            return
        if kind == 'error':
            failure = value
            panel.set_status(f'啟動失敗 / Startup failed: {value}\n日誌: {LOG_PATH}')
            if closing or on_ready is not None:
                root.destroy()
                return
        else:
            services = value
            if closing:
                threading.Thread(target=stop, daemon=True).start()
            else:
                panel.set_locale(services.locale)
                panel.refresh(services.monitor.snapshot())
                panel.set_ready(True)
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

    def toggle():
        nonlocal busy
        if services is None or busy or closing:
            return
        busy = True
        panel.set_ready(False)
        def change_monitor():
            try:
                if services.monitor.snapshot().get('enabled'):
                    services.monitor.stop()
                else:
                    services.monitor.start()
            except Exception:
                log_event(logging.getLogger('sweety.windows'), 'monitor_toggle_failed', exc_info=True)
            finally:
                events.put(('changed', services))
        threading.Thread(target=change_monitor, name='SweetyToggle', daemon=True).start()

    panel = WindowsPanel(root, toggle=toggle,
        manage=lambda: webbrowser.open(MANAGEMENT_URL), quit=close)
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
