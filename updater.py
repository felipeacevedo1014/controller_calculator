import requests
import os
import sys
import tempfile
import subprocess
from tkinter import messagebox

# ✅ Your remote files (hosted on GitHub)
REPO_LATEST_VERSION_URL = "https://raw.githubusercontent.com/felipeacevedo1014/controller_calculator/refs/heads/main/version.txt"
REPO_EXE_URL = "https://github.com/felipeacevedo1014/controller_calculator/releases/latest/download/controller_calculator.exe"

# ✅ Your current version
APP_VERSION = "1.0.0"  # Update this with each release

def check_for_updates():
    try:
        response = requests.get(REPO_LATEST_VERSION_URL, timeout=5)
        response.raise_for_status()
        latest_version = response.text.strip()

        if latest_version != APP_VERSION:
            result = messagebox.askyesno(
                "Update Available",
                f"A new version ({latest_version}) is available.\n\nDo you want to download and install it now?"
            )
            if result:
                download_and_run_new_version()
    except Exception as e:
        print(f"[Updater] Version check failed: {e}")

def download_and_run_new_version():
    try:
        response = requests.get(REPO_EXE_URL, stream=True)
        response.raise_for_status()

        temp_dir = tempfile.gettempdir()
        new_path = os.path.join(temp_dir, "controller_calculator_updated.exe")

        with open(new_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        subprocess.Popen([new_path])
        sys.exit(0)

    except Exception as e:
        messagebox.showerror("Update Failed", f"Could not download update:\n{e}")
