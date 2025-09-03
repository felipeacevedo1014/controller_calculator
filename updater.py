# updater.py — use GitHub latest release tag
import webbrowser
import requests
from packaging.version import Version

OWNER = "felipeacevedo1014"
REPO  = "controller_calculator"

LATEST_API   = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{OWNER}/{REPO}/releases/latest"

def _current_version() -> Version:
    # Single source of truth from your bundled version.py
    from version import __version__
    return Version(str(__version__).strip().lstrip("vV"))

def _latest_release_version(token: str | None = None) -> Version:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(LATEST_API, headers=headers, timeout=6)
    r.raise_for_status()
    tag = (r.json().get("tag_name") or "").strip()
    if not tag:
        raise RuntimeError("No tag_name in latest release response")
    return Version(tag.lstrip("vV"))

def check_for_updates():
    try:
        cur = _current_version()
        latest = _latest_release_version()  # pass GH token here if repo is private
        print(f"[Updater] Current version: {cur}, Latest version: {latest}")
        if latest > cur:
            # keep it ultra-simple: ask & open the page
            try:
                from tkinter import Tk, messagebox
                root = Tk(); root.withdraw()
                if messagebox.askyesno(
                    "Update Available",
                    f"A newer version is available.\n\nCurrent: {cur}\nLatest:  {latest}\n\n"
                    "Open the GitHub Releases page?"
                ):
                    webbrowser.open(RELEASES_URL)
                root.destroy()
            except Exception:
                webbrowser.open(RELEASES_URL)
    except Exception as e:
        print(f"[Updater] Failed to check latest release: {e}")

if __name__ == "__main__":
    check_for_updates()
