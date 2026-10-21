"""Install an official Node 24 runtime privately, without sudo or system changes."""
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from .config import DATA_DIR

ROOT = DATA_DIR/'Library/Application Support/Outlook Assistant/node' if DATA_DIR == Path.home() else DATA_DIR/'node'


def executable():
    for path in sorted(ROOT.glob('v24.*/bin/node'), key=lambda p: tuple(int(n) for n in p.parents[1].name[1:].split('.')), reverse=True):
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


def download(url, destination, limit):
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(url, timeout=45) as response, destination.open('wb') as output:
        while True:
            chunk = response.read(1024*1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise ValueError('The Node download exceeds the expected size.')
            output.write(chunk); digest.update(chunk)
    return digest.hexdigest()


def unpack(archive, destination, prefix):
    """Reject traversal, links outside the runtime, devices and oversized archives."""
    root = destination.resolve()
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        if len(members) > 30000 or sum(m.size for m in members) > 500*1024*1024:
            raise ValueError('Unexpected Node archive size.')
        for member in members:
            parts = Path(member.name).parts
            if not parts or parts[0] != prefix or '..' in parts or Path(member.name).is_absolute():
                raise ValueError('Unsafe Node archive path.')
            target = root.joinpath(*parts[1:])
            if not (member.isdir() or member.isfile() or member.issym()):
                raise ValueError('Unsupported Node archive entry.')
            if member.issym():
                resolved = (target.parent/member.linkname).resolve()
                if os.path.commonpath([root, resolved]) != str(root):
                    raise ValueError('Unsafe Node archive link.')
        # Write regular files first; no archive symlink participates in file writes.
        for member in members:
            target = root.joinpath(*Path(member.name).parts[1:])
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
        for member in members:
            if member.issym():
                target = root.joinpath(*Path(member.name).parts[1:]);target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(member.linkname)


def install():
    if platform.system() != 'Darwin' or platform.machine() not in ('arm64', 'x86_64'):
        raise ValueError('Automatic setup supports Apple silicon and Intel Macs.')
    with urllib.request.urlopen('https://nodejs.org/dist/index.json', timeout=20) as response:
        releases = json.loads(response.read(2_000_000))
    versions = [r['version'] for r in releases if re.fullmatch(r'v24\.\d+\.\d+', r.get('version', ''))]
    if not versions:
        raise ValueError('No supported Node release found.')
    version = max(versions, key=lambda v: tuple(map(int,v[1:].split('.'))))
    arch = 'arm64' if platform.machine() == 'arm64' else 'x64'
    prefix = f'node-{version}-darwin-{arch}';name = prefix+'.tar.gz'
    base = 'https://nodejs.org/dist/'+version+'/'
    with urllib.request.urlopen(base+'SHASUMS256.txt', timeout=20) as response:
        hashes = response.read(100000).decode()
    expected = next((line.split()[0] for line in hashes.splitlines() if len(line.split()) == 2 and line.split()[1] == name), '')
    if not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('Node release checksum is missing.')
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='.setup-', dir=ROOT) as folder:
        stage = Path(folder);archive = stage/'node.tar.gz'
        if download(base+name, archive, 100*1024*1024) != expected:
            raise ValueError('Node download checksum did not match. Please retry.')
        runtime = stage/'runtime';runtime.mkdir();unpack(archive, runtime, prefix)
        checked = subprocess.run([str(runtime/'bin/node'), '--version'], capture_output=True, text=True, timeout=10)
        if checked.returncode or checked.stdout.strip() != version:
            raise ValueError('Downloaded Node runtime could not start on this Mac.')
        target = ROOT/version
        if target.exists():
            raise ValueError('A runtime with this version already exists. Repair it before retrying.')
        runtime.rename(target)
    return str(target/'bin/node')
