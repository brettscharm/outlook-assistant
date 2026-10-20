"""Private, atomic per-user settings; secrets are never returned to the browser."""
import json
import os
import tempfile
import threading
from pathlib import Path

CONFIG_PATH = Path.home() / '.outlook_assistant_config.json'
_LOCK = threading.RLock()


def read_config():
    with _LOCK:
        try:
            return json.loads(CONFIG_PATH.read_text())
        except FileNotFoundError:
            return {}


def update_config(values):
    with _LOCK:
        data = read_config()
        data.update(values)
        fd, name = tempfile.mkstemp(dir=CONFIG_PATH.parent, prefix='.outlook-config-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(data, stream)
            os.replace(name, CONFIG_PATH)
        finally:
            if os.path.exists(name):
                os.unlink(name)
