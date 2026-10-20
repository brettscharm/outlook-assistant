"""Explicit, serialized updates. Never overwrite a dirty checkout or extract unsafe paths."""
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import urllib.request
from pathlib import Path

GITHUB_REPO='brettscharm/outlook-assistant'
_LOCK=threading.Lock()

def get_latest_github_commit():
    req=urllib.request.Request(f'https://api.github.com/repos/{GITHUB_REPO}/commits/main',headers={'User-Agent':'OutlookAssistant/2.0'})
    with urllib.request.urlopen(req,timeout=15) as r: return json.load(r)['sha']


def check_and_apply_update(repo_dir=None,auto_pull=False):
    target=Path(repo_dir) if repo_dir else Path(__file__).resolve().parent.parent
    if not _LOCK.acquire(blocking=False): return False,'An update is already in progress.'
    try:
        if (target/'.git').is_dir():
            def git(*args):
                return subprocess.run(['git',*args],cwd=target,capture_output=True,text=True,timeout=40,check=True).stdout.strip()
            if git('status','--porcelain'): return False,'Local changes are present. Update skipped to protect them.'
            git('fetch','origin','main')
            current=git('rev-parse','HEAD'); latest=git('rev-parse','origin/main')
            if current==latest: return False,'You are up to date.'
            if not auto_pull: return True,'An update is available.'
            git('merge','--ff-only','origin/main')
            return True,'Update installed. Restarting…'
        latest=get_latest_github_commit()
        stamp=target/'.installed_commit'
        if stamp.exists() and stamp.read_text().strip()==latest: return False,'You are up to date.'
        if not auto_pull: return True,'An update is available.'
        with tempfile.TemporaryDirectory(prefix='outlook-update-') as tmp:
            archive=Path(tmp)/'update.tar.gz'
            urllib.request.urlretrieve(f'https://api.github.com/repos/{GITHUB_REPO}/tarball/{latest}',archive)
            staging=Path(tmp)/'extracted';staging.mkdir()
            with tarfile.open(archive) as tar:
                for member in tar.getmembers():
                    dest=(staging/member.name).resolve()
                    if not dest.is_relative_to(staging.resolve()) or not (member.isfile() or member.isdir()):
                        raise ValueError('Unsafe update archive.')
                tar.extractall(staging)
            source=next(staging.iterdir())
            if not (source/'outlook_plugin/app_server.py').is_file(): raise ValueError('Invalid update.')
            from . import __version__
            version_text=(source/'outlook_plugin/__init__.py').read_text()
            match=re.search(r'__version__\s*=\s*[\"\']([0-9.]+)',version_text)
            if not match or tuple(map(int,match[1].split('.'))) < tuple(map(int,__version__.split('.'))):
                raise ValueError('This download is older than your installed app. Update skipped.')
            # Stage complete package beside target, then replace it with rollback on failure.
            pending=target/'.outlook_plugin_next';backup=target/'.outlook_plugin_previous'
            shutil.rmtree(pending,ignore_errors=True)
            shutil.copytree(source/'outlook_plugin',pending)
            shutil.rmtree(backup,ignore_errors=True)
            os.replace(target/'outlook_plugin',backup)
            try: os.replace(pending,target/'outlook_plugin')
            except Exception:
                os.replace(backup,target/'outlook_plugin');raise
            stamp.write_text(latest)
            shutil.rmtree(backup,ignore_errors=True)
        return True,'Update installed. Restarting…'
    except Exception as exc:
        return False,'Update could not be installed: '+str(exc)[:300]
    finally: _LOCK.release()


def run_background_update_check():
    return None
