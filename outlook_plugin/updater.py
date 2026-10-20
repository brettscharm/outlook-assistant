"""
Robust Auto-Updater module for Outlook Assistant
Works for BOTH Git clones AND standalone ZIP downloads from GitHub.
"""

import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

GITHUB_REPO = "brettscharm/outlook-assistant"
UPDATE_CHECK_INTERVAL = 1800  # Check every 30 minutes
CACHE_FILE = Path.home() / ".outlook_assistant_update_cache.json"


def get_latest_github_commit() -> Optional[str]:
    """Fetch the latest commit SHA from GitHub API."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "OutlookAssistant-Updater/1.0", "Accept": "application/vnd.github.v3+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("sha", "")[:7]
    except Exception as e:
        logger.debug(f"GitHub commit check error: {e}")
        return None


def check_and_apply_update(repo_dir: Optional[str] = None, auto_pull: bool = True) -> Tuple[bool, str]:
    """
    Check if an update is available and apply it automatically.
    Works for both Git clones and Standalone ZIP downloads.
    """
    target_dir = repo_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_dir = os.path.join(target_dir, ".git")

    # MODE 1: Git repository
    if os.path.isdir(git_dir):
        try:
            fetch_cmd = subprocess.run(
                ["git", "fetch", "--quiet"],
                cwd=target_dir,
                capture_output=True,
                timeout=10,
                text=True,
            )
            if fetch_cmd.returncode == 0:
                local_hash = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=target_dir, text=True
                ).strip()
                remote_hash = subprocess.check_output(
                    ["git", "rev-parse", "@{u}"], cwd=target_dir, text=True
                ).strip()

                if local_hash == remote_hash:
                    return False, "Already up to date."

                if auto_pull:
                    pull_cmd = subprocess.run(
                        ["git", "pull", "--ff-only"],
                        cwd=target_dir,
                        capture_output=True,
                        timeout=15,
                        text=True,
                    )
                    if pull_cmd.returncode == 0:
                        return True, f"Updated successfully to commit {remote_hash[:7]}!"
                    else:
                        return False, f"Git pull failed: {pull_cmd.stderr.strip()}"
                else:
                    return True, f"New version available ({remote_hash[:7]})"
        except Exception as e:
            logger.debug(f"Git update failed: {e}")

    # MODE 2: Standalone ZIP download fallback
    try:
        remote_sha = get_latest_github_commit()
        if not remote_sha:
            return False, "Could not check GitHub for updates."

        local_version_file = Path(target_dir) / ".installed_commit"
        current_sha = local_version_file.read_text().strip() if local_version_file.exists() else "initial"

        if current_sha == remote_sha:
            return False, f"Already up to date ({remote_sha})."

        if not auto_pull:
            return True, f"New version available on GitHub ({remote_sha})."

        # Download tarball and extract
        tarball_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.tar.gz"
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_tar:
            urllib.request.urlretrieve(tarball_url, tmp_tar.name)
            with tarfile.open(tmp_tar.name, "r:gz") as tar:
                with tempfile.TemporaryDirectory() as extract_dir:
                    tar.extractall(extract_dir)
                    subfolder = os.path.join(extract_dir, f"outlook-assistant-main")
                    if os.path.isdir(subfolder):
                        # Copy updated files over target_dir
                        for item in os.listdir(subfolder):
                            s = os.path.join(subfolder, item)
                            d = os.path.join(target_dir, item)
                            if os.path.isdir(s):
                                shutil.copytree(s, d, dirs_exist_ok=True)
                            else:
                                shutil.copy2(s, d)

        local_version_file.write_text(remote_sha)
        return True, f"Updated to latest GitHub version ({remote_sha})!"

    except Exception as e:
        logger.debug(f"Standalone update error: {e}")
        return False, f"Update check error: {e}"


def run_background_update_check():
    """Lightweight non-blocking background check."""
    now = time.time()
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                last_check = data.get("last_check", 0)
                if now - last_check < UPDATE_CHECK_INTERVAL:
                    return

        with open(CACHE_FILE, "w") as f:
            json.dump({"last_check": now}, f)

        check_and_apply_update(auto_pull=True)
    except Exception:
        pass
