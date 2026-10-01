# Phase 2 Report — Repository, Engineering Foundation and Design System

**Phase:** 2 of 18 — Repository, engineering foundation and design system
**Date:** 2026-10-01
**Branch:** `arena/01a0f67e-dentivaproofficial`
**Phase commit:** `0011dae` (CI run [36836992197](https://github.com/kshohanservice-glitch/dentivaproofficial/actions/runs/36836992197) — **all jobs green**)
**Status: COMPLETE — every Phase 2 acceptance item passes, with CI evidence. Awaiting the owner's pull-request decision; no PR is merged by the agent.**

> The foundation was partly built in a previous session on the sibling branch
> `arena/01a0f649-…`. This session took that work over, re-verified it locally, diagnosed and fixed
> every CI failure, added the quality gates the documentation promised, re-aligned the plan to the
> specification's 18 phases, and produced the first fully green end-to-end Windows pipeline.

---

## 1. What the repository contains (verified, not assumed)

| Area | Delivered |
|---|---|
| Project & tooling | `pyproject.toml` (src layout, every runtime dependency pinned), ruff (29 rule families), strict mypy on `src/dentivapro`, pytest with markers/timeouts, coverage configuration, `.gitignore`, `.gitattributes` |
| Design system | `ui/design/tokens.py` (colour, typography, spacing, radii, elevation, motion, metrics, breakpoints), `theme.py` (single stylesheet keyed by object name/variant/state, palette, shadows), `fonts.py` (bundled Inter + Noto Sans Bengali with Bengali detection and size handling), `icons.py` (62-icon SVG subset, tinting, DPI-aware pixmaps) |
| Components | primitives (text, buttons, fields, banners, chips, menu actions), cards, data table (virtualised model), page, states (empty/loading/error/permission-denied/development), toast |
| Shell | navigation model (17 routes in Practice/Clinical/Billing/Administration, permission-gated), router with history, collapsible sidebar (240 ↔ 68 px), header (identity, clinic, live date, honest disabled search/notifications, user menu), keyboard shortcuts, main window with error boundary, status bar, toasts |
| Screens | About (product identity, creator details, diagnostics, open-source notices) and the development state used by modules that later phases implement |
| Core | errors, paths (documented data-root resolution incl. `DENTIVAPRO_DATA_ROOT`), structured JSONL logging with redaction and rotation, money (`Decimal` over integer paisa; floats rejected), time utilities (Bengali digits, date views, age), configuration, id/patient-code generation, i18n, worker framework, typed settings registry |
| Data | connection layer (WAL, foreign keys, transactional helpers, typed errors), migration discovery/ordering with schema history and newer-schema refusal, `001_base.sql`, repositories (base, meta, sequence, settings) |
| Security foundations | permission catalogue (domain layer), secret scanner, activation design documented and reserved for Phase 3 |
| Assets | bundled fonts (OFL-1.1), icon set, licence notices, multi-resolution application icon (`.ico` with 9 sizes 16–256 px, transparent corners, symmetric 9 px margins at 256 px) |
| Packaging | PyInstaller onedir spec (icon and version resource embedded), NSIS installer (per-user, Start Menu shortcut, optional desktop shortcut, Add/Remove Programs entry, uninstaller with an explicit clinic-data choice), version-resource generator, bundle auditor |
| Tests | 320 tests: unit, integration, services, UI/shell, acceptance, design-system contract, golden rendering (13 committed Linux goldens with fingerprints) |
| CI | `.github/workflows/ci.yml`: quality job (ruff, format, mypy, secret scan, static gates), Linux test job, Windows job (tests, bundle build, bundle audit + offscreen launch, installer build, silent install → launch → verify → uninstall, artifact upload) |

## 2. Work completed in this session

| # | Work | Evidence |
|---|---|---|
| 1 | Repository hand-over verified from scratch on the session branch: commits, files, tests, CI runs, artefact state | 309 tests passing locally before any change; CI history read through the API |
| 2 | Fixed the failing Windows pipeline through five defect rounds (see §3) until the job is green | CI run 36836992197: `quality`, `tests-linux`, `windows-build` all `success` |
| 3 | Implemented the static quality gates the documentation promised: `tools/qa/check_no_placeholders.py`, `check_money.py`, `check_offline.py`, `check_traceability.py`, `check_all.py`, with a README and unit tests | `python tools/qa/check_all.py` → "all 4 static gates passed"; wired into the CI quality job |
| 4 | Re-aligned the plan to the specification's 18 phases (no phase merged or skipped) and renumbered every phase reference in source, docs and packaging | `docs/phase-plan.md`, `docs/requirements-traceability.md` (120 rows re-mapped), navigation labels, i18n strings, shortcut notes |
| 5 | Re-promoted the Linux golden baseline for the deliberate label changes | 10 goldens updated; golden suite green |
| 6 | Corrected documentation that did not match the implementation (missing `requirements.lock`, missing gate scripts, stale job name, makensis path semantics) | `docs/architecture/06` and `08`, `packaging/README.md` |
| 7 | Added a failure-diagnostics capability so a red CI run can be diagnosed without downloading logs (this is how the remaining defects were found) | workflow step + annotation output visible on the failing runs |

## 3. Defects found and fixed (root causes, not guesses)

| # | Defect | Root cause | Fix |
|---|---|---|---|
| 2-1 | Windows job failed auditing the bundle | the auditor matched substrings against the self-check output | parse `key : value` fields (previous session; verified green here) |
| 2-2 | Installer step failed with exit 127 | `windows-latest` now tracks windows-2025, which does not ship NSIS (windows-2022 does) | locate `makensis`, install it with Chocolatey when missing, hard-fail when it cannot be found; runner pinned to windows-2022 with the reason documented |
| 2-3 | Installer step failed with exit 1: `Can't open script "C:/Program Files/Git/DPRODUCT_VERSION=1.0.0"` | Git Bash converted the `/D…` switch into a POSIX path | `MSYS_NO_PATHCONV` / `MSYS2_ARG_CONV_EXCL` for the packaging tools (also protects the installer's `/S` switch) |
| 2-4 | Installer compile failed even with correct paths | makensis switches its working directory to the script's folder, so `dist\…` resolved to `packaging\dist\…` | pass absolute Windows paths (`cygpath -w`), document the behaviour in the script header and the packaging README |
| 2-5 | NSIS compile error in the uninstaller page | the script used the `${NSD_*}` macros without including `nsDialogs.nsh` (MUI2 does not provide them) | include `nsDialogs.nsh` (+ `WinMessages.nsh` for `${BST_*}`), and give the installer/uninstaller the product icon while there |
| 2-6 | Uninstaller would never delete the machine-wide data folder when asked | `$PROGRAMDATA` is not an NSIS constant (makensis warned about it) | read it with `ReadEnvStr`, guarded, and keep `$LOCALAPPDATA` (a real constant) |
| 2-7 | Smoke test reported a healthy installation as broken | it substring-matched "integrity check ok", but the self-check prints `integrity check : ok` | match the fields with a regular expression and verify journal mode, schema version, table count and first-run state |
| 2-8 | Uninstall left the application on disk | the uninstall section deleted the runtime folder and the uninstaller but never the executable, so the final `RMDir` could not remove the folder | delete exactly what was installed (executable, runtime folder, uninstaller), then remove the folder only if empty |

## 4. Verification evidence

### 4.1 Development sandbox (Linux, offscreen Qt), at the phase commit

| Check | Command | Result |
|---|---|---|
| Test suite | `pytest -q -p no:randomly` | **320 passed** (16.1 s) |
| Lint | `ruff check .` | clean |
| Format | `ruff format --check .` | 114 files formatted |
| Types | `mypy` (strict) | no issues in 62 source files |
| Static gates | `python tools/qa/check_all.py` | all 4 gates pass |
| Secrets | `python tools/secret_scan.py` | clean (228 files) |
| Application start | `python -m dentivapro --check` | initialised database, WAL, schema 1, foreign keys on, integrity ok, bundled fonts ok, 5 tables, setup not complete |
| Data-root override | `DENTIVAPRO_DATA_ROOT=… --check` | honoured (used by the CI smoke test) |
| Git | working tree clean, branch == origin | — |

### 4.2 CI (GitHub Actions, run 36836992197 @ `0011dae`)

| Job | Result | Evidence |
|---|---|---|
| Lint, format, types and secret scan | **success** | ruff, format, strict mypy, secret scan, static gates |
| Test suite (Linux) | **success** | full pytest suite on ubuntu-latest |
| Windows bundle, installer and smoke test | **success** | PyInstaller bundle built and audited; packaged application launched offscreen and initialised/verified its database; **NSIS installer built (30 MB, LZMA, zero warnings)**; silent install placed the application and created the Start Menu shortcut; the installed application reported `journal mode : wal`, `foreign keys : on`, `integrity check : ok`, `bundled fonts : ok`, `schema version : 1`, `tables : 5`, `setup complete : no`; silent uninstall removed the application and the shortcut |
| Artifacts | available to the owner | `dentivapro-windows` (74.4 MB: onedir bundle + installer), `ui-renders-windows`, `ui-renders-linux` |

## 5. Acceptance gate

| Gate item | Status |
|---|---|
| Repository structure, dependency management, lint/format/type configuration, testing infrastructure, migration foundation, logging, configuration, secret handling | **Pass** |
| UI design system and application shell foundation (header, sidebar, routing, components, states, shortcuts, High-DPI handling) | **Pass** |
| Shell renders correctly at every supported window size and display scale, with committed golden fingerprints | **Pass** (13 goldens, re-promoted for this phase's label changes) |
| Application starts, initialises its database and reports a clean integrity check | **Pass** |
| Windows job builds the `.exe`, builds the installer, installs silently, launches, verifies database initialisation, uninstalls | **Pass** (first fully green run) |
| Every quality gate green in CI | **Pass** |
| Pull request opened for review, **not merged by the agent** | **Open for the owner** (see §7) |

## 6. Honest gaps carried forward (documented, not hidden)

1. **Windows golden baseline not promoted.** The renders are produced and uploaded by every Windows run
   (`ui-renders-windows`); promoting them is deliberately the owner's review step
   (`python tools/promote_goldens.py`). Until then, Windows golden checks skip with an explicit message
   instead of passing silently.
2. **Installer hardening and clean-machine validation belong to Phase 17** — all-users install mode,
   desktop-shortcut option coverage, the clinic-data deletion path (not exercised by CI, which keeps its
   data in a temporary root) and the physical-printer checklist.
3. **The installer is unsigned** (no certificate exists for this project); Windows SmartScreen will warn
   on first run, and the release notes must say so.
4. **Dark theme is not implemented** because the specification asks for a premium light clinical theme;
   this is stated rather than shipped as a half-working toggle. Note that the theme is token-driven, so
   adding one later is a contained change.
5. **CI log/artifact download from this sandbox is blocked** (signed URLs point at a host this environment
   cannot reach). Runs, step results and annotations are readable, and the workflow publishes its own
   failure output; artifacts are downloaded by the owner from the Actions UI.

## 7. Pull request

The phase work is pushed to `arena/01a0f67e-dentivaproofficial` and offered as a pull request against
`main`. **The agent does not merge pull requests.** PR #1 (opened by the previous session's branch)
covers an earlier state of the same work; this branch supersedes it and includes the CI fixes.

## 8. Next phase

**Phase 3 — Database, Domain Model, Security and RBAC**: the complete relational schema and migrations,
repositories, domain services, Argon2id authentication, sessions and auto-lock, granular RBAC enforced in
the service/query layer, the append-only audit foundation, activation verification, and the security test
suite. It starts only when the owner says **Continue**.

**Phase 2 is complete. Awaiting "Continue" for Phase 3.**
