# Environment Capabilities and Honest Limitations

This document records what was empirically verified in the development environment during Phase 1, what
could not be verified here, and how each gap is closed. Nothing in this file is an assumption: every entry
comes from a command whose result is summarised below.

## 1. Verified capabilities

| Capability | Evidence (Phase 1 probe) | Consequence for the project |
|---|---|---|
| Python 3.11 sandbox, 3.12 targeted for Windows bundles | `python3 --version`, `pip download --platform win_amd64 --python-version 3.12` | Windows runtime is Python 3.12; development/tests run on 3.11 locally and 3.12 in CI |
| PySide6 6.11.2 (Qt 6) installs and runs headless | `pip install PySide6-Essentials`; offscreen render + PDF written | The real UI toolkit is fully testable here (goldens, interactions, PDF) |
| Qt renders Bengali correctly with bundled fonts | `qtprobe2.py` → `qtprobe2.png` (conjuncts ক্ষ জ্ঞ ন্ত ষ্ট র্ম ট্র দ্ব প্র ঞ্চ হ্ম, ৳, Bengali digits all correct) | Bengali requirement is proven feasible and testable locally |
| Qt prints to PDF offline | `QPdfWriter` produced a valid A5 PDF (13 KB) with Bengali table content | PDF path is real, not theoretical |
| SQLite in Python with WAL and FTS5 available | `sqlite3` version 3.40.1, `PRAGMA compile_options` | Database architecture matches the runtime that ships with Windows Python 3.12 (SQLite ≥ 3.37) |
| Large-dataset performance is adequate | 100 000 patient rows inserted in 0.89 s; indexed prefix search 0.12 ms; paged query 9.4 ms; Qt model with 20 000 rows renders in 0.04 s | The performance budgets in `06-testing-and-quality.md` are realistic |
| Argon2id works and is fast enough | hash + verify round trip, 76 ms per hash at m=64 MiB/t=3/p=2 | Password security approach is validated at the intended cost |
| All production wheels exist for Windows | `pip download --platform win_amd64` succeeded for PySide6-Essentials, shiboken6, argon2-cffi(+bindings), cryptography, pyinstaller, platformdirs, segno, pytest, pytest-qt, ruff, mypy, pypdf, Pillow | The dependency set is real and installable for the target platform before any code is written |
| Google Fonts repositories are reachable through the GitHub API | fonts and OFL licence texts written to disk (463 KB Bengali, 876 KB Inter) | Fonts can be vendored legally and reproducibly |
| GitHub push/PR capability | `git ls-remote` and `gh pr list` succeed with the provided token | Branch/PR workflow is possible |
| PyInstaller is functional (Linux) | analysis stage runs; fails only because the sandbox Python is not built with `--enable-shared` | The spec file is developed and validated here; the Windows bundle is produced in CI |

## 2. Verified limitations

| Limitation | Evidence | Impact | Mitigation |
|---|---|---|---|
| No Windows machine or emulator available | Linux only; `wine` absent and `apt` unreachable | The EXE and the installer cannot be executed here | All Windows-specific validation runs on GitHub Actions `windows-latest` (bundle smoke test, goldens, installer build + installer smoke test) and the manual clean-machine checklist in Phase 17 |
| `.NET`/NuGet unreachable | `api.nuget.org`, `packages.microsoft.com` → connection failure | Rules out a WPF/.NET stack in this environment | Not needed: the chosen stack is Python/Qt |
| GitHub release-asset CDN blocked | `objects.githubusercontent.com` → no connection | Electron runtimes, apt packages, some binaries cannot be downloaded | Chosen stack depends only on PyPI, which is reachable |
| Sandbox Python lacks shared library | PyInstaller analysis error | Local EXE bundling is impossible | Bundling is a CI responsibility; the spec is tested in CI |
| Actions/K8s-style API scope missing on the token | `gh api .../actions/permissions` → 403 | CI run status/logs may not be readable from here | the CI workflow is verified in Phase 2 and its outcome reported honestly; if unavailable, the release report states it and relies on the user's account permissions |
| No physical printers | No hardware in a sandbox | Real device behaviour cannot be proven here | Print layout is validated by rendering to PDF/PNG across the paper matrix; the physical printer checklist is manual in Phase 17 |
| No Bengali-capable Windows font assurance | Sandbox lacks Bengali fonts by default | Rendering would show boxes without our fonts | Fonts are bundled in the app; a runtime check blocks printing if the font cannot load |
| No antivirus/SmartScreen environment | Sandbox | Code-signing effect cannot be demonstrated | Signing is implemented in CI when a certificate exists; otherwise the release is explicitly documented as unsigned |

## 3. What this means for the release claim

The final release report will state precisely which checks ran in which environment. Claims of
"clean-machine tested" are only made when the clean-machine checklist has actually been executed and its
evidence attached. The activation design document states the honest cryptographic limitation of any
purely offline activation scheme, and no claim of perfect secrecy is made.

## 4. Sandbox-only development scaffolding (never shipped)

To render Qt in this sandbox, four small stub shared libraries are generated
(`libGL.so.1`, `libEGL.so.1`, `libxkbcommon.so.0`, `libdbus-1.so.3`, plus a `libQt6DBus.so.6` symbol stub)
that satisfy the loader for headless operation. They exist solely inside the sandbox tooling
(`tools/devsandbox/`), are used only via `LD_LIBRARY_PATH` during development/test runs, and are
**never** part of the application, the bundle, the installer or the repository's runtime path. Windows
builds do not use them. A packaging test asserts that `dist/` contains none of these files.
