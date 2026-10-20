"""Private, atomic per-user settings; secrets are never returned to the browser."""
import json
import os
import tempfile
import threading
from pathlib import Path

DATA_DIR = Path(os.environ.get('OUTLOOK_ASSISTANT_DATA_DIR', str(Path.home()))).expanduser()
if 'OUTLOOK_ASSISTANT_DATA_DIR' in os.environ:
    DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
from .storage import read_json, write_json

CONFIG_PATH = DATA_DIR / '.outlook_assistant_config.json'
_LOCK = threading.RLock()


def read_config():
    with _LOCK:
        return read_json(CONFIG_PATH,{})


def update_config(values):
    with _LOCK:
        data = read_config()
        data.update(values)
        write_json(CONFIG_PATH,data)
