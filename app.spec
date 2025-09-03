# app.spec — build with:  pyinstaller app.spec
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = (
    ["customtkinter", "PIL", "PIL.Image", "PIL.ImageTk", "requests", "pandas", "numpy"]
    + collect_submodules("PIL")
)

# Remove lines for files you don't actually have.
datas = [
    ("assets", "assets"),   # images folder used by gui.py
    ("version.py", "."),    # your version file (optional but recommended)
    ("tooltip.py", "."),    # only if you import tooltip.py
]

a = Analysis(
    ['gui.py'],    # entrypoint GUI
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='points_calculator',  # final exe name
    console=False,             # True if you want a console for logs
    debug=False,
    strip=False,
    upx=True,
    icon=None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='points_calculator'   # dist folder name
)
