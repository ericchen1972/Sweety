"""Keep piped helper processes in the background on Windows."""
import subprocess
import sys


def background_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}


class BackgroundSubprocess:
    """Module-local adapter; never change the global subprocess module."""

    def __init__(self, module):
        self.module = module

    def __getattr__(self, name):
        return getattr(self.module, name)

    def _options(self, kwargs):
        options = background_options()
        if options:
            kwargs['creationflags'] = kwargs.get('creationflags', 0) | options['creationflags']
        return kwargs

    def Popen(self, *args, **kwargs):
        return self.module.Popen(*args, **self._options(kwargs))

    def run(self, *args, **kwargs):
        return self.module.run(*args, **self._options(kwargs))


def configure_line_background_processes():
    if sys.platform == 'win32':
        from okline import hmac_signer
        if not isinstance(hmac_signer.subprocess, BackgroundSubprocess):
            hmac_signer.subprocess = BackgroundSubprocess(hmac_signer.subprocess)
