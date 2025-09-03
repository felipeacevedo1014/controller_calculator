# updater.py
from __future__ import annotations
import os
import sys
import json
import time
import traceback
from pathlib import Path
from typing import Optional
import zipfile
import shutil
import subprocess
import tempfile

# --- Third-party
import requests
from packaging.version import Version, InvalidVersion

OWNER = "felipeacevedo1014"
REPO = "controller_calculator"
GITHUB_API = f"https://api.github.com/repos/{OWNER}/{REPO}"

# --- Logging setup (ALWAYS ON) ---
def _app_dir() -> Path:
    # Put log beside the EXE if frozen, else in cwd
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()

LOG = _app_dir() / "updater.log"

def _log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg + "\n")
    except Exception:
        # last-ditch: print to console
        print(msg, file=sys.stderr)

def _log_exc(prefix: str) -> None:
    _log(prefix + "\n" + traceback.format_exc())

# --- Version helpers ---
def _current_version() -> Version:
    try:
        from version import __version__  # your project's file
        v = str(__version__).strip()
        _log(f"current_version (from version.py): {v}")
        return Version(v.lstrip("vV"))
    except Exception:
        _log_exc("Failed to import version.__version__; trying VERSION file")
        vf = _app_dir() / "VERSION"
        if vf.exists():
            v = vf.read_text().strip()
            _log(f"current_version (from VERSION file): {v}")
            return Version(v.lstrip("vV"))
        raise

def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        _log("Using GitHub token from env.")
    return headers

def _latest_release_version() -> Version:
    url = f"{GITHUB_API}/releases/latest"
    _log(f"GET {url}")
    r = requests.get(url, headers=_github_headers(), timeout=12)
    _log(f"GitHub status: {r.status_code}")
    r.raise_for_status()
    data = r.json()
    tag = (data.get("tag_name") or "").strip()
    if not tag:
        raise RuntimeError("Latest release has no tag_name.")
    try:
        v = Version(tag.lstrip("vV"))
        _log(f"latest_release tag_name={tag} parsed={v}")
        return v
    except InvalidVersion:
        raise RuntimeError(f"Bad semver tag: {tag!r}")

def _is_update_available(cur: Version, latest: Version) -> bool:
    return latest > cur

# --- Public entry point expected by gui.py ---
def check_for_updates() -> Optional[tuple[Version, Version]]:
    """
    Returns (cur, latest) if an update is available, else None.
    Always logs details to updater.log.
    """
    _log("=== check_for_updates: START ===")
    try:
        cur = _current_version()
    except Exception:
        _log_exc("Failed to get current version")
        return None

    try:
        latest = _latest_release_version()
    except Exception:
        _log_exc("Failed to fetch latest release")
        return None

    _log(f"Compare: cur={cur}, latest={latest}")
    if _is_update_available(cur, latest):
        _log("Update AVAILABLE.")
        # Minimal proof-of-life UI so you SEE it:
        try:
            _notify_update_available(cur, latest)
        except Exception:
            _log_exc("Failed to show notification UI (non-fatal)")
        return (cur, latest)
    else:
        _log("No update available.")
        return None

# --- Visual cue (works even if your custom UI has issues) ---
def _notify_update_available(cur: Version, latest: Version) -> None:
    # Try Tkinter messagebox (since you already use Tk)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Update available",
            f"A new version is available.\n\nCurrent: {cur}\nLatest:  {latest}\n\n"
            "Proceed with your updater flow."
        )
        root.destroy()
        _log("Tkinter messagebox shown.")
        return
    except Exception:
        _log_exc("Tkinter messagebox failed; falling back to console print")
    # Console fallback
    print(f"[UPDATER] Update available: {cur} -> {latest}")



# ... keep your existing imports / logging / version funcs ...

import zipfile
import shutil
import subprocess
import tempfile

# === Choose assets you publish in Releases ===
PREFERRED_ASSET_PATTERNS = [
    ".exe",  # installer exe (preferred)
    ".msi",  # installer msi
    ".zip",  # portable zip
]

def _get_latest_release_json():
    url = f"{GITHUB_API}/releases/latest"
    _log(f"GET {url}")
    r = requests.get(url, headers=_github_headers(), timeout=20)
    _log(f"GitHub status: {r.status_code}")
    r.raise_for_status()
    return r.json()

def _pick_asset(data: dict) -> dict | None:
    assets = data.get("assets") or []
    if not assets:
        _log("No assets on latest release.")
        return None
    # simple preference order by extension
    def pref_idx(name: str) -> int:
        name = name.lower()
        for i, ext in enumerate(PREFERRED_ASSET_PATTERNS):
            if name.endswith(ext):
                return i
        return 999
    assets_sorted = sorted(assets, key=lambda a: pref_idx(a.get("name","")))
    chosen = assets_sorted[0] if assets_sorted else None
    if chosen:
        _log(f"Chosen asset: {chosen.get('name')} ({chosen.get('size')} bytes)")
    return chosen

def _download_asset(asset: dict, dest_dir: Path) -> Path:
    # Public repos: browser_download_url works. Private: still works with token in headers.
    url = asset.get("browser_download_url")
    name = asset.get("name") or "download.bin"
    if not url:
        raise RuntimeError("Asset missing browser_download_url")
    dest = dest_dir / name
    _log(f"Downloading asset: {url} -> {dest}")
    with requests.get(url, headers=_github_headers(), stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
    _log(f"Downloaded {dest} ({dest.stat().st_size} bytes)")
    return dest

def _run_installer(path: Path) -> None:
    _log(f"Launching installer: {path}")
    # Try silent/passive switches; if your installer uses different switches, change here.
    try_switches = [
        [str(path), "/passive"],
        [str(path), "/S"],     # NSIS / Inno Setup style
        [str(path)],           # no switches fallback
    ]
    for cmd in try_switches:
        try:
            subprocess.Popen(cmd, cwd=path.parent)
            _log(f"Installer started: {' '.join(cmd)}")
            return
        except Exception:
            _log_exc(f"Failed to start installer with {cmd}")
    raise RuntimeError("Failed to launch installer")

def _extract_zip(zip_path: Path, extract_to: Path) -> Path:
    _log(f"Extracting zip: {zip_path} -> {extract_to}")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
    _log("Zip extracted.")
    return extract_to

def _app_dir() -> Path:
    # (You already have this, but keep consistent)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()

def _current_exe_path() -> Path:
    return Path(sys.executable) if getattr(sys, "frozen", False) else None

def _spawn_ps_update_helper(src_dir: Path, target_dir: Path, relaunch_exe: str) -> None:
    """
    Create and run a PowerShell script that:
      1) waits for this process to exit,
      2) copies files from src_dir into target_dir,
      3) starts relaunch_exe,
      4) deletes src_dir and itself.
    """
    ps_path = target_dir / "apply_update.ps1"
    proc_name = Path(sys.executable).name if getattr(sys, "frozen", False) else "python.exe"
    script = f"""
$ErrorActionPreference = "Stop"
$src = "{str(src_dir)}"
$dst = "{str(target_dir)}"
$exe = "{relaunch_exe}"
$me  = "{str(ps_path)}"

# 1) wait for running process to exit (up to 60s)
$deadline = (Get-Date).AddSeconds(60)
while ((Get-Process | Where-Object {{$_.Name -ieq "{proc_name}"}}) -and (Get-Date) -lt $deadline) {{
    Start-Sleep -Seconds 1
}}

# 2) copy files over (robust copy)
robocopy $src $dst /E /NFL /NDL /NJH /NJS /NP /R:2 /W:1 | Out-Null

# 3) relaunch
Start-Process -FilePath (Join-Path $dst $exe) | Out-Null

# 4) cleanup
Start-Sleep -Seconds 1
try {{ Remove-Item -Recurse -Force $src }}
catch {{ }}
try {{ Remove-Item -Force $me }}
catch {{ }}
"""
    ps_path.write_text(script, encoding="utf-8")
    _log(f"Wrote PS helper: {ps_path}")
    # Run it detached
    subprocess.Popen([
        "powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(ps_path)
    ], cwd=target_dir, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    _log("PS helper launched.")

def _perform_update_flow(latest: Version) -> None:
    """
    After user confirmation, download and apply the update.
    """
    data = _get_latest_release_json()
    asset = _pick_asset(data)
    if not asset:
        _log("No asset found. Opening releases page for user.")
        import webbrowser
        webbrowser.open(f"https://github.com/{OWNER}/{REPO}/releases/latest")
        return

    tmp = Path(tempfile.mkdtemp(prefix="cc_upd_"))
    try:
        payload = _download_asset(asset, tmp)
        name_low = payload.name.lower()
        if name_low.endswith(".exe") or name_low.endswith(".msi"):
            _run_installer(payload)
            _log("Installer started; exiting app (installer will handle).")
            # optional: exit app so installer can replace files
            os._exit(0)
        elif name_low.endswith(".zip"):
            extracted = _extract_zip(payload, tmp / "extracted")
            target_dir = _app_dir()
            # Try to figure which exe to relaunch
            exe_name = Path(sys.executable).name if getattr(sys, "frozen", False) else None
            if not exe_name:
                # dev mode: just open the folder for manual copy
                _log("Not frozen; opening extracted folder instead of self-replacing.")
                import webbrowser
                webbrowser.open(str(extracted))
                return
            _spawn_ps_update_helper(extracted, target_dir, exe_name)
            _log("Update helper spawned; exiting app.")
            os._exit(0)
        else:
            _log(f"Unsupported asset type: {payload.name}")
            import webbrowser
            webbrowser.open(f"https://github.com/{OWNER}/{REPO}/releases/latest")
    finally:
        # temp dir cleaned by PS helper if zip path; otherwise, system will reclaim later
        pass

# === Replace your notify to actually do the update ===
def _notify_update_available(cur: Version, latest: Version) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        ans = messagebox.askyesno(
            "Update available",
            f"A new version is available.\n\nCurrent: {cur}\nLatest:  {latest}\n\n"
            "Do you want to update now?"
        )
        root.destroy()
        _log(f"User chose update: {ans}")
        if ans:
            _perform_update_flow(latest)
    except Exception:
        _log_exc("notify/update flow failed; falling back to browser open")
        try:
            import webbrowser
            webbrowser.open(f"https://github.com/{OWNER}/{REPO}/releases/latest")
        except Exception:
            _log_exc("Failed to open releases page")


if __name__ == "__main__":
    check_for_updates()
