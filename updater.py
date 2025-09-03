# updater.py
import os, sys, json, tempfile, shutil, subprocess, time
import requests
from version import __version__, __app_name__

GITHUB_OWNER = "felipeacevedo1014"     # <-- CHANGE
GITHUB_REPO  = "controller_calculator" # <-- CHANGE
API_URL      = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

def _is_frozen():
    return getattr(sys, 'frozen', False)

def _current_exe_path():
    # Path of the running executable (PyInstaller)
    if _is_frozen():
        return sys.executable
    # Running from source: write next to this script (for dev test)
    return os.path.abspath(sys.argv[0])

def get_latest_release():
    r = requests.get(API_URL, timeout=15)
    r.raise_for_status()
    return r.json()

def parse_semver(v):
    return tuple(int(p) for p in v.strip("v").split("."))

def is_newer(remote_tag, local_version):
    try:
        return parse_semver(remote_tag) > parse_semver(local_version)
    except Exception:
        # Fallback to string compare if needed
        return str(remote_tag).strip("v") != str(local_version).strip("v")

def pick_windows_asset(assets):
    for a in assets:
        if a.get("name","").lower() == "points_calculator.exe":
            return a
    return None

def prompt_user(msg):
    # Minimal prompt; replace with tkinter messagebox if you prefer
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        return messagebox.askyesno("Update available", msg)
    except Exception:
        resp = input(f"{msg} [y/N]: ").strip().lower()
        return resp.startswith("y")

def check_for_updates():
    try:
        data = get_latest_release()
        remote_tag = data.get("tag_name") or data.get("name")
        if not remote_tag:
            return

        if not is_newer(remote_tag, __version__):
            return

        asset = pick_windows_asset(data.get("assets", []))
        if not asset:
            return

        url  = asset["browser_download_url"]
        size = asset.get("size", 0)
        msg = (f"A new version of {__app_name__} is available.\n\n"
               f"Current: {__version__}\n"
               f"Latest:  {remote_tag}\n"
               f"Download size: ~{size//1024} KB\n\n"
               "Update now?")
        if not prompt_user(msg):
            return

        # Download to temp
        tmpdir = tempfile.mkdtemp(prefix="updater_")
        new_exe = os.path.join(tmpdir, asset["name"])
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(new_exe, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024*256):
                    if chunk:
                        f.write(chunk)

        # Swap in place using PowerShell (Windows)
        current_exe = _current_exe_path()
        target_exe  = current_exe

        # If running from source, put the exe next to current script (dev aid)
        if not _is_frozen():
            target_exe = os.path.join(os.path.dirname(current_exe), os.path.basename(new_exe))

        ps = r'''
$old  = "{old}"
$new  = "{new}"
$dest = "{dest}"

Start-Sleep -Milliseconds 400
# Try multiple times in case the app hasn't fully exited
$attempts = 0
while($attempts -lt 20) {{
  try {{
    if (Test-Path $dest) {{ Remove-Item -Force $dest }}
    Copy-Item -Force $new $dest
    Start-Process -FilePath $dest
    break
  }} catch {{
    Start-Sleep -Milliseconds 250
    $attempts++
  }}
}}
'''.format(old=current_exe.replace("\\", "\\\\"),
           new=new_exe.replace("\\", "\\\\"),
           dest=target_exe.replace("\\", "\\\\"))

        # Launch PS to replace after we exit
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])
        # Exit the current app so PS can replace the file
        os._exit(0)

    except Exception as e:
        # Silent fail is fine in production; or log/print if you prefer
        # print("Update check failed:", e)
        return
