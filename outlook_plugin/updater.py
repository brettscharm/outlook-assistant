"""
Auto-Updater module for Outlook Assistant
Checks GitHub repository for updates and keeps all client machines automatically in sync.
"""

import json
import logging
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

UPDATE_CHECK_INTERVAL = 43200  # Check every 12 hours (in seconds)
CACHE_FILE = Path.home() / ".outlook_assistant_update_cache.json"


def check_and_apply_update(repo_dir: Optional[str] = None, auto_pull: bool = True) -> Tuple[bool, str]:
    """
    Check if a newer version exists in the git repository and optionally pull it.
    
    Returns:
        (updated: bool, message: str)
    """
    target_dir = repo_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_dir = os.path.join(target_dir, ".git")

    if not os.path.isdir(git_dir):
        return False, "Not a git repository (standalone installation)."

    try:
        # Fetch latest commit info from remote
        fetch_cmd = subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=target_dir,
            capture_output=True,
            timeout=10,
            text=True,
        )
        if fetch_cmd.returncode != 0:
            return False, "Could not reach remote repository."

        # Check local vs remote HEAD
        local_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=target_dir, text=True
        ).strip()
        remote_hash = subprocess.check_output(
            ["git", "rev-parse", "@{u}"], cwd=target_dir, text=True
        ).strip()

        if local_hash == remote_hash:
            return False, "Already up to date."

        if auto_pull:
            # Pull changes automatically
            pull_cmd = subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=target_dir,
                capture_output=True,
                timeout=15,
                text=True,
            )
            if pull_cmd.returncode == 0:
                logger.info("Successfully updated Outlook Assistant to the latest version.")
                return True, f"Updated successfully to latest version ({remote_hash[:7]})."
            else:
                return False, f"Update pull failed: {pull_cmd.stderr.strip()}"
        else:
            return True, f"New update available ({remote_hash[:7]})."

    except Exception as e:
        logger.debug(f"Auto-update check failed: {e}")
        return False, f"Update check error: {e}"


def run_background_update_check():
    """Lightweight check to ensure users don't face latency on every command."""
    now = time.time()
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                last_check = data.get("last_check", 0)
                if now - last_check < UPDATE_CHECK_INTERVAL:
                    return
        
        # Save timestamp
        with open(CACHE_FILE, "w") as f:
            json.dump({"last_check": now}, f)

        # Check and pull
        check_and_apply_update(auto_pull=True)
    except Exception:
        pass
