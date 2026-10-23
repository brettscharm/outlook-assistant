"""Pinned standalone Python for speech tools; never changes system Python."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

URL='https://github.com/astral-sh/python-build-standalone/releases/download/20261021/cpython-3.12.15%2B20261021-aarch64-apple-darwin-install_only_stripped.tar.gz'
SHA256='7b8d00b751db21cea87dc551a8f8165147c5fbc5251d5537d7e5497dde00a219'


def install(root):
    if platform.system()!='Darwin' or platform.machine()!='arm64':raise ValueError('Local transcription requires an Apple silicon Mac.')
    if int(platform.mac_ver()[0].split('.')[0])<14:raise ValueError('Local transcription requires macOS 14 or later.')
    root=Path(root);root.mkdir(parents=True,exist_ok=True,mode=0o700)
    destination=root/'python-3.12.15';python=destination/'bin/python3'
    environment=root/'runtime-v2';executable=environment/'bin/python3'
    lock=Path(__file__).with_name('speech-requirements.txt')
    fingerprint=hashlib.sha256(lock.read_bytes()).hexdigest()
    ready=environment/'ready'
    if executable.exists() and ready.exists() and ready.read_text()==fingerprint:return executable
    if shutil.disk_usage(root).free<3_000_000_000:raise ValueError('Free at least 3 GB for local speech tools and models.')
    try:
        if not python.exists():
            with tempfile.TemporaryDirectory(prefix='speech-install-',dir=root) as scratch:
                archive=Path(scratch)/'python.tar.gz'
                subprocess.run(['/usr/bin/curl','--fail','--location','--silent','--show-error','--retry','2','--max-time','300','--output',str(archive),URL],check=True,capture_output=True,timeout=330)
                if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise ValueError('Speech runtime verification failed. Retry setup.')
                # The exact upstream archive is authenticated by the pinned SHA-256 above.
                subprocess.run(['/usr/bin/tar','-xzf',str(archive),'-C',scratch],check=True,capture_output=True,timeout=90)
                if not (Path(scratch)/'python/bin/python3').is_file():raise ValueError('The speech runtime is incomplete.')
                if destination.exists():shutil.rmtree(destination)
                os.replace(Path(scratch)/'python',destination)
        subprocess.run([str(python),'-m','venv',str(environment)],check=True,capture_output=True,timeout=120)
        subprocess.run([str(executable),'-m','pip','install','--disable-pip-version-check','--only-binary=:all:','--requirement',str(lock)],check=True,capture_output=True,timeout=900)
    except (OSError,subprocess.SubprocessError) as exc:
        raise ValueError('Could not set up local speech tools. Check your internet connection and available disk space, then retry. Your recording is saved.') from exc
    ready.write_text(fingerprint);ready.chmod(0o600)
    return executable
