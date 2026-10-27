"""Exercise the Windows host with an offline monitor; never start real LINE."""
import sys
from types import SimpleNamespace

import pytest

from sweety_app.panel_text import panel_ui_copy, status_text


@pytest.mark.parametrize('language_id,expected', [
    (0x0404, 'zh-TW'), (0x0C04, 'zh-TW'), (0x1404, 'zh-TW'),
    (0x7C04, 'zh-TW'), (0x0804, 'en'), (0x0411, 'en'), (0x0409, 'en'),
])
def test_windows_display_language(language_id, expected):
    from sweety_app.config import windows_ui_locale
    assert windows_ui_locale(language_id) == expected


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows display language')
def test_display_language_overrides_python_regional_locale(monkeypatch):
    import ctypes
    from sweety_app.config import preferred_locale
    monkeypatch.setattr(ctypes, 'WinDLL', lambda name: SimpleNamespace(GetUserDefaultUILanguage=lambda: 0x0404))
    assert preferred_locale('Chinese (Traditional)_Taiwan') == 'zh-TW'
    assert preferred_locale('en_US') == 'zh-TW'


def test_shared_panel_status_keeps_login_errors_and_localized_controls():
    assert panel_ui_copy('zh-TW')['start'] == '開始'
    assert panel_ui_copy('ja')['stop'] == '停止'
    assert status_text('zh-TW', {'status': 'line_login_required'}) == '請先到管理介面登入 LINE'
    assert status_text('en', {'status': 'error', 'message': 'offline detail'}) == 'Error (offline detail)'


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows native panel')
def test_window_controls_refresh_monitor_and_close_without_reopening_browser(monkeypatch):
    from sweety_app import windows

    calls, failures = [], []
    snapshot = dict(enabled=False, status='stopped', selectedTargetCount=3)

    def start():
        calls.append('start')
        snapshot.update(enabled=True, status='monitoring')

    def stop():
        calls.append('stop')
        snapshot.update(enabled=False, status='stopped')

    services = SimpleNamespace(locale='zh-TW',
        monitor=SimpleNamespace(snapshot=lambda: dict(snapshot), start=start, stop=stop),
        stop=lambda: calls.append('shutdown'))
    original = windows.WindowsPanel

    class TestPanel(original):
        def __init__(self, root, **kwargs):
            super().__init__(root, **kwargs)
            self.phase = 0
            root.after(250, self.exercise)
            root.after(10000, lambda: (failures.append('UI timeout'), root.destroy()))

        def exercise(self):
            button = self.buttons['toggle'][0]
            if str(button['state']) == 'disabled':
                self.root.after(50, self.exercise)
                return
            try:
                assert self.root.winfo_width() == self.root.winfo_height() == 500
                assert self.canvas.itemcget(self.count, 'text') == '3'
                for name in ('toggle', 'manage', 'quit'):
                    assert self.buttons[name][0]['image']
                if self.phase == 0:
                    self.set_locale('en')
                    self.root.update_idletasks()
                    for control, _shape in self.buttons.values():
                        assert control.winfo_reqwidth() <= control.winfo_width(), 'English label clips its icon'
                    self.set_locale('zh-TW')
                    assert '開始' in button['text']
                    assert str(button['image']) == str(self.icons['play'])
                    button.invoke()
                elif self.phase == 1:
                    assert '停止' in button['text']
                    assert button['bg'] == '#ff453a'
                    assert str(button['image']) == str(self.icons['stop'])
                    assert self.canvas.itemcget(self.status, 'text') == '正在監控新訊息'
                    button.invoke()
                else:
                    assert '開始' in button['text']
                    assert button['bg'] == '#0084ff'
                    self.buttons['quit'][0].invoke()
                    return
                self.phase += 1
                self.root.after(200, self.exercise)
            except Exception as exc:
                failures.append(str(exc))
                self.buttons['quit'][0].invoke()

    monkeypatch.setattr(windows, 'WindowsPanel', TestPanel)
    monkeypatch.setattr(windows.webbrowser, 'open', lambda url: calls.append('browser'))
    windows.run_window(factory=lambda: services)
    assert not failures
    assert calls.count('browser') == 1
    assert calls.count('start') == calls.count('stop') == 1
    assert 'shutdown' in calls
