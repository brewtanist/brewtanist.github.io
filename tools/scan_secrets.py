"""Pinned Gitleaks scan: full Git history plus the current files, with redacted output."""
import hashlib
import io
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '8.30.1'
RELEASES = {
    'Windows': ('windows_x64.zip', 'd29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e', 'gitleaks.exe'),
    'Linux': ('linux_x64.tar.gz', '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb', 'gitleaks'),
}


def main():
    suffix, expected, executable = RELEASES[platform.system()]
    if platform.machine().lower() not in ('amd64', 'x86_64'):
        raise SystemExit('Only the verified x64 release is supported')
    url = f'https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/gitleaks_{VERSION}_{suffix}'
    with urllib.request.urlopen(url, timeout=60) as response:
        archive = response.read(32 * 1024 * 1024)
    if hashlib.sha256(archive).hexdigest() != expected:
        raise SystemExit('Scanner download checksum mismatch; refusing to execute')
    with tempfile.TemporaryDirectory(prefix='website-gitleaks-') as tmp:
        target = Path(tmp) / executable
        # Extract only the expected executable, never arbitrary archive paths.
        if suffix.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(archive)) as package:
                target.write_bytes(package.read(executable))
        else:
            with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as package:
                target.write_bytes(package.extractfile(executable).read())
        os.chmod(target, 0o700)
        for mode, extra in [('git', ['--log-opts=--all']), ('dir', [])]:
            subprocess.run([str(target), mode, '--redact=100', '--no-banner', '--log-level=warn',
                            *extra, str(ROOT)], cwd=ROOT, check=True)
    print('PASS: Gitleaks scanned all available Git refs and current files; findings are redacted.')


if __name__ == '__main__':
    main()
