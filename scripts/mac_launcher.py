"""Frozen bootstrap: Python stays bundled; reviewed app source can update independently."""
import argparse
import importlib
import os
import sys
import urllib.request
import webbrowser
from pathlib import Path


def main():
    if getattr(sys,'frozen',False):
        bundled=Path(sys.executable).resolve().parents[1]/'Resources'/'app'
        root=Path.home()/'Library/Application Support/Outlook Assistant/app'
        if not (root/'outlook_plugin/app_server.py').exists():
            import shutil
            root.mkdir(parents=True,exist_ok=True,mode=0o700)
            shutil.copytree(bundled/'outlook_plugin',root/'outlook_plugin')
        sys.path.insert(0,str(root))
    else:
        root=Path(__file__).resolve().parent.parent
        sys.path.insert(0,str(root))
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8484)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    try:
        with urllib.request.urlopen(f'http://localhost:{args.port}/api/health',timeout=2) as r:
            import json
            data=json.load(r)
        if data.get('instance'):
            if not args.no_browser: webbrowser.open(f'http://localhost:{args.port}')
            return
    except Exception: pass
    # Explicit imports let the packager discover all standard-library dependencies.
    from outlook_plugin.app_server import start_app_server
    start_app_server(args.port,not args.no_browser)

if __name__=='__main__': main()
