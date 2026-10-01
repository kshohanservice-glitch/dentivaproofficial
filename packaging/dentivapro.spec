# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build description for Dentiva Pro (onedir, windowed).

Build (Windows; the release artifact is produced in CI, never by hand):

    python packaging/make_version_info.py
    pyinstaller --noconfirm --clean packaging/dentivapro.spec

The result is ``dist/DentivaPro/`` with ``DentivaPro.exe`` inside, which the NSIS script
(``packaging/installer.nsi``) turns into the installer. onedir is used rather than onefile: it starts
faster, keeps the Qt DLLs as replaceable files (LGPL compliance for the Qt runtime), and lets the
installer verify individual files.

Asset layout matters: the application resolves its assets relative to its own package
(``Path(__file__).parents[2] / "assets"``), so the datas below must land under ``dentivapro/…`` in the
bundle, exactly mirroring ``src/dentivapro/…``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

REPO_ROOT = Path(SPECPATH).resolve().parent
SRC = REPO_ROOT / "src"
sys.path.insert(0, str(SRC))

from dentivapro.version import APP_EXECUTABLE, APP_SLUG, APP_NAME  # noqa: E402

PACKAGE = SRC / "dentivapro"
ASSETS = PACKAGE / "assets"

# Data files the running application reads. Missing fonts/icons/schema are a hard startup failure, so
# these entries are the difference between a working bundle and a broken one.
datas = [
    (str(ASSETS / "fonts"), "dentivapro/assets/fonts"),
    (str(ASSETS / "icons"), "dentivapro/assets/icons"),
    (str(ASSETS / "notices"), "dentivapro/assets/notices"),
    (str(ASSETS / "branding"), "dentivapro/assets/branding"),
    (str(PACKAGE / "data" / "db" / "schema"), "dentivapro/data/db/schema"),
]

hiddenimports = [
    "PySide6.QtSvg",  # icon rendering
    "PySide6.QtPrintSupport",  # printing and PDF output (phases 5+)
] + collect_submodules("dentivapro.data.repos")

# Modules that must never ship: development tooling, test frameworks, documentation generators and the
# parts of Qt this product does not use. Keeping them out shrinks the installer and reduces attack surface.
excludes = [
    "tkinter",
    "unittest",
    "doctest",
    "pydoc",
    "pdb",
    "setuptools",
    "pip",
    "wheel",
    "pytest",
    "_pytest",
    "pluggy",
    "numpy",
    "pandas",
    "PIL",
    "pypdf",
    "PyInstaller",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtRemoteObjects",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtUiTools",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
]

version_file = REPO_ROOT / "packaging" / "version_info.txt"
if sys.platform.startswith("win") and not version_file.exists():
    raise SystemExit(
        "packaging/version_info.txt is missing; run: python packaging/make_version_info.py"
    )

a = Analysis(  # noqa: F821 - provided by PyInstaller
    [str(PACKAGE / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_EXECUTABLE,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX packing trips antivirus heuristics and breaks minidumps; not worth the ~30 % size
    console=False,  # GUI application: no console window for clinic staff
    disable_windowed_traceback=False,
    icon=str(ASSETS / "branding" / "app_icon.ico"),
    version=str(version_file) if sys.platform.startswith("win") else None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_SLUG,
)

# Kept for the smoke test and the report: the build is identified by name and version only.
print(f"built {APP_NAME} {APP_EXECUTABLE} (onedir, no console)")
