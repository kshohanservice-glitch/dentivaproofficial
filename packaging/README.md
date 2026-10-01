# Windows packaging

Everything in this folder is used by the CI packaging job (`.github/workflows/ci.yml`, `windows-bundle`).
The released installer is produced there, never by hand in the development sandbox (which has no Windows).

| File | Purpose |
|---|---|
| `dentivapro.spec` | PyInstaller onedir build: EXE plus the Qt runtime, bundled fonts, icons, notices and schema SQL |
| `make_version_info.py` | Generates `version_info.txt` (Windows file properties) from `src/dentivapro/version.py` |
| `installer.nsi` | NSIS 3 installer: per-user install, Start Menu shortcut, optional desktop shortcut, Add/Remove Programs entry, uninstaller with explicit clinic-data choice |
| `check_bundle.py` | Bundle smoke test: contents audit plus (on Windows) launching the EXE offscreen and initialising a database |

## Building (Windows)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -e ".[dev]"          # pinned versions from pyproject.toml
.venv\Scripts\python packaging\make_version_info.py
.venv\Scripts\pyinstaller --noconfirm --clean packaging\dentivapro.spec
.venv\Scripts\python packaging\check_bundle.py dist\DentivaPro
& "${env:ProgramFiles(x86)}\NSIS\makensis.exe" /DPRODUCT_VERSION=1.0.0 `
    /DSOURCE_DIR=dist\DentivaPro packaging\installer.nsi
```

Artifacts land in `dist/`: `dist/DentivaPro/` (application) and
`dist/DentivaPro-Setup-<version>.exe` (installer).

## Honest status

* **Code signing:** the installer and EXE are **unsigned** — no signing certificate exists for this
  project. Windows SmartScreen will warn on first run; the release notes must state this. Signing is
  wired into CI only if a real certificate is provided, and it is never faked.
* **Per-user install:** this script installs for the current user (no administrator prompt). An optional
  all-users mode is part of the Phase 11 installer hardening together with the clean-machine test.
* **Installer smoke test:** silent install → launch → verify database initialisation → uninstall runs on
  the CI Windows runner; the physical clean-machine checklist is Phase 11.
* **Clinic data is never removed silently:** the uninstaller only deletes the data folder when the user
  ticks the checkbox *and* confirms the warning.

## Bundle contents

The bundle must contain the application package, the Qt runtime, bundled fonts
(`Inter.ttf`, `NotoSansBengali.ttf`), the icon set, the licence notices and `dentivapro/data/db/schema`.
It must *not* contain test code, development tooling, sample data or any `.db` file — `check_bundle.py`
enforces both lists and fails the build otherwise.
