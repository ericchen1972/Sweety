"""Wrap the release onedir in an Inno Setup installer without user data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib


def validate_package(package: Path) -> None:
    required = ('Sweety.exe', '_internal/runtime-config.json', '_internal/runtime/node.exe',
                '_internal/frontend/index.html', '_internal/assets/panel-background.png')
    for relative in required:
        if not (package / relative).is_file():
            raise ValueError(f'Release file missing: {relative}')
    setting = json.loads((package / '_internal/runtime-config.json').read_text(encoding='utf-8'))
    if str(setting.get('SWEETY_LOG_ENABLED')) != '0':
        raise ValueError('Installer requires a release built with --logging 0')
    for path in package.rglob('*'):
        if path.is_symlink():
            raise ValueError(f'Symlink not permitted in installer: {path}')
        if path.is_file() and (path.suffix.lower() in {'.session', '.sqlite3', '.db', '.log', '.env'}
                              or '.sweety' in path.relative_to(package).parts):
            raise ValueError(f'User data must not be packaged: {path}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--iscc', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Build the installer on Windows')
    package, output = args.package.resolve(), args.output.resolve()
    validate_package(package)
    output.mkdir(parents=True, exist_ok=True)
    desktop = Path(__file__).resolve().parent
    version = tomllib.loads((desktop / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    from PIL import Image
    with Image.open(desktop.parents[1] / 'web/images/logo.png') as image:
        image.convert('RGBA').save(output / 'Sweety.ico', format='ICO',
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    subprocess.run([str(args.iscc.resolve()), f'/DPackageDir={package}',
        f'/DAppVersion={version}', f'/DBuildDir={output}', str(desktop / 'Sweety-Setup.iss')], check=True)
    installer = output / f'Sweety-Windows-Setup-{version}.exe'
    if installer.read_bytes()[:2] != b'MZ':
        raise ValueError('Invalid installer executable')
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    installer.with_suffix('.exe.sha256').write_text(f'{digest}  {installer.name}\n', encoding='ascii')
    print(installer)


if __name__ == '__main__':
    main()
