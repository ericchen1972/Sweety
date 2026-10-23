"""Build a self-contained Windows x64 onedir test ZIP (run on Windows)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--logging', choices=('0', '1'), default='1',
                        help='SWEETY_LOG_ENABLED bundled value: tests=1, releases=0')
    args = parser.parse_args()
    if sys.platform != 'win32' or sys.maxsize <= 2**32:
        parser.error('Build using 64-bit Python on Windows.')
    desktop = Path(__file__).resolve().parent
    project = desktop.parents[1]
    build = args.output.resolve()
    build.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, SWEETY_BUILD_ROOT=str(build), SWEETY_LOG_ENABLED=args.logging)

    subprocess.run(['npm.cmd', 'ci'], cwd=project / 'app/frontend', check=True)
    subprocess.run(['npm.cmd', 'run', 'build', '--', '--outDir', str(build / 'frontend'),
                    '--emptyOutDir'], cwd=project / 'app/frontend', check=True)

    # Use the official Windows distribution, including its LICENSE and OpenSSL notices.
    node_version = 'v22.14.0'
    node_archive = f'node-{node_version}-win-x64.zip'
    base = f'https://nodejs.org/dist/{node_version}/'
    archive = build / node_archive
    urllib.request.urlretrieve(base + node_archive, archive)
    sums = urllib.request.urlopen(base + 'SHASUMS256.txt', timeout=60).read().decode()
    expected = next(line.split()[0] for line in sums.splitlines() if line.split()[-1] == node_archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Node distribution checksum mismatch')
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(build / 'node-download')
    node = build / 'node'
    node.mkdir(exist_ok=True)
    distribution = build / 'node-download' / f'node-{node_version}-win-x64'
    shutil.copy2(distribution / 'node.exe', node / 'node.exe')
    notices = build / 'third-party'
    notices.mkdir(exist_ok=True)
    shutil.copy2(distribution / 'LICENSE', notices / 'Node-LICENSE.txt')
    shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', notices / 'Python-LICENSE.txt')
    shutil.copy2(project / 'docs/third-party-okline.md', notices)
    (build / 'runtime-config.json').write_text(
        json.dumps({'SWEETY_LOG_ENABLED': args.logging}), encoding='utf-8')
    from PIL import Image
    with Image.open(project / 'web/images/logo.png') as image:
        image.convert('RGBA').save(build / 'Sweety.ico', format='ICO',
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    subprocess.run([sys.executable, '-m', 'PyInstaller', str(desktop / 'Sweety-Windows.spec'),
        '--noconfirm', '--clean', '--workpath', str(build / 'work'),
        '--distpath', str(build / 'dist')], cwd=desktop, env=environment, check=True)
    package = build / 'dist/Sweety'
    shutil.copy2(desktop / 'WINDOWS-README.txt', package / 'README.txt')
    # Keep the archive as a single top-level folder; never copy developer sessions.
    archive_path = Path(shutil.make_archive(str(build / 'Sweety-2.0.0-Windows-x64-portable-test'),
                        'zip', root_dir=build / 'dist', base_dir='Sweety'))
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    archive_path.with_suffix('.zip.sha256').write_text(f'{digest}  {archive_path.name}\n', encoding='ascii')
    print(archive_path)


if __name__ == '__main__':
    main()
