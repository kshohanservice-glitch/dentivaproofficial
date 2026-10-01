# Phase 1 report — Foundation, design system and Windows shell

**Branch:** `arena/01a0f649-dentivaproofficial` · **Base:** `af9fb3e` (Phase 0) · **Phase:** 1 of 13
**Date:** 2026-10-01 · **Prepared by:** implementation agent

---

## 1. What was built

| Area | Delivered |
|---|---|
| Repository & tooling | `pyproject.toml` (src layout, pinned dependencies, ruff/mypy/pytest/coverage configuration), `.gitignore`, `.gitattributes`, `tools/` (`icons/generate_app_icon.py`, `secret_scan.py`, `promote_goldens.py`, `devsandbox/`) |
| Design system | `ui/design/tokens.py` (light palette, typography, spacing, radii, elevation, motion, metrics, breakpoints 1600/1280/1024/900), `theme.py` (single stylesheet by `objectName` + `variant`/`state`, palette, shadows, reduced-motion), `fonts.py` (bundled Inter + Noto Sans Bengali, Bengali detection/size bump), `icons.py` (62 SVG Lucide subset, tinting, DPI-aware pixmaps) |
| Components | `ui/components/` — primitives (`Text`, buttons, fields, banners, chips, `make_menu_action`, spacer), `cards.py`, `states.py` (empty/loading/error/permission-denied/development states), `toast.py`, `page.py`, `data_table.py` (virtualised model) |
| Shell | `ui/shell/` — `navigation.py` (17 routes across Practice/Clinical/Billing/Administration with permission + phase metadata), `router.py` (history, permission denial reporting), `sidebar.py` (collapsible 240 ↔ 68 px, permission filtering, exact labels), `header.py` (identity, clinic, live date, honest disabled search/notifications, user + help menus), `shortcuts.py`, `main_window.py` (route hosting, error boundary, toasts, status bar, foundation banner), `ui/dialogs/shortcuts_dialog.py` |
| Screens | `ui/screens/about_screen.py` (product identity, creator Shohan Khan helloiamshohan@gmail.com, diagnostics card, bundled open-source notices), `ui/screens/pending_screen.py` (explicit "not available in this build yet" state for future modules) |
| Core | `core/` — errors, paths (data-root resolution order incl. env override), structured JSONL logging with redaction, money (`Money` over `Decimal`, float rejection), time utilities (Bengali digits, date views, humanised age), config, IDs/patient codes, i18n, worker framework, settings schema (typed registry) |
| Data | `data/db/connection.py` (WAL, foreign keys, transactional helpers, typed errors), `migrations.py` (discovery, ordering, newer-schema refusal, history), `schema/001_base.sql`, `data/repos/` (base, meta, sequence, settings) |
| Services | `services/settings_service.py` (typed get/set/reset with validation and change events) |
| Assets | Bundled fonts (OFL-1.1), icon set, licence notices, app icon set (16–256 px + `.ico`) |
| Tests | `tests/` — 302 tests (unit, integration, services, UI/shell, acceptance, design-system static gate, golden rendering store) |
| Packaging | `packaging/dentivapro.spec` (PyInstaller onedir), `packaging/installer.nsi` (NSIS 3 per-user installer with explicit clinic-data choice on uninstall), `packaging/make_version_info.py` (+ generated `version_info.txt`), `packaging/check_bundle.py`, `packaging/README.md` |
| CI | `.github/workflows/ci.yml` — `quality` (ruff, format, strict mypy, secret scan), `tests-linux` (full suite + render artefacts), `windows-build` (tests, PyInstaller bundle, bundle audit + offscreen launch, NSIS installer, silent install/launch/uninstall smoke test, artefact upload) |
| Docs | This report; traceability statuses advanced for the Phase 1 rows |

## 2. Verification (commands and results)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check .` | **All checks passed** (started the phase at 153 findings, all fixed rather than ignored) |
| Format | `ruff format --check .` | **104 files already formatted** |
| Types | `mypy` (strict, `src/dentivapro`) | **Success: no issues found in 62 source files** (started at 32 errors) |
| Tests | `QT_QPA_PLATFORM=offscreen python -m pytest -q -p no:randomly` (with the sandbox Qt stubs) | **302 passed, 0 failed** (~14 s) |
| Secrets | `python tools/secret_scan.py` | **clean (218 files)** — no activation literal, keys or tokens in the repository |
| Shell renders | `tests/ui/test_golden_screens.py` + `tests/ui/goldens/linux/` | 13 committed goldens (4 window sizes, 4 display scales, collapsed sidebar, compact header, about screen, pending-module screen, toast, data table) — fingerprinted at 16×12 averaged-colour cells with a documented tolerance, stable across runs (verified by re-render + hash comparison, and by tampering a golden to prove the gate fails) |
| App startup | `python -m dentivapro --check` | opens/initialises `dentivapro.db`, reports `schema version 1`, `foreign keys on`, `integrity check ok`, `bundled fonts ok`, `tables 5`, `setup complete no` |
| Bundle audit | `python packaging/check_bundle.py <bundle>` | verified both directions against a synthetic bundle: passes a clean bundle, fails one containing a database file or test code |
| Version resource | `python packaging/make_version_info.py --check` | matches `version.py` (`1.0.0`); the malformed 3-tuple found during the work was fixed to the required 4-tuple |
| CI definition | YAML parsed and job/step structure inspected | valid: 3 jobs, triggers push/PR/manual, `fail-fast` semantics not applicable (no matrix) |

Environment limitations that shaped the work (documented in `docs/environment-and-limitations.md`):

* **No Windows in this sandbox**, and the sandbox Python is built without a shared library, so PyInstaller
  stops at `Python shared library ('libpython3.11.so.1.0') was not found`. The spec itself was validated by
  running PyInstaller to the Analysis stage (all paths, data collection, hidden imports and excludes are
  processed without a spec error) and by building the fake-bundle audit above. **The EXE and installer are
  produced only by the `windows-build` CI job.**
* The offscreen Qt platform on this image needs loader-only stubs for `libGL`/`libEGL`/`libxkbcommon`/
  `libdbus-1`; the recipe lives in `tools/devsandbox/` and is used only for development (CI installs the
  real packages). `libQt6DBus.so.6` is never stubbed — Qt must resolve its own `Qt_6` version node.

## 3. Defects found during the phase and fixed

| Defect | Impact | Fix |
|---|---|---|
| Fixed-width block in the state panel | The shell could not shrink below 1181 px, so a 1024 px laptop gained a horizontal scrollbar and the compact header never engaged | `setMaximumWidth` instead of `setFixedWidth`; explicit supported window minimum 1024×720 (`QLayout.SetNoConstraint` + `setMinimumSize`) |
| Unescaped `&` in sidebar labels | "Staff & Users" rendered as "Staff _Users" with a mnemonic underline | labels escaped centrally (`_button_label`) with tooltips keeping the plain text; regression test asserts the rendered text |
| Malformed PyInstaller version resource | `filevers=1, 0, 0` would have failed the Windows EXE build | generator emits the required 4-tuple `(1, 0, 0, 0)`; `--check` runs in CI before packaging |
| Stale design-system/lint/type debt | 153 ruff findings and 32 mypy errors at the start of the phase | all fixed in source (no blanket ignores); the remaining suppressions are documented per-line with a reason |

## 4. Not achieved in this phase (honest status)

1. **CI run status could not be determined from the sandbox.** The workflow is pushed, but every Actions API
   call from this token returns HTTP 404 (`gh run list` empty, `repos/…/actions/runs` 404,
   `actions/permissions` 404), so neither triggering nor reading a run is possible here. The phase gate
   item "CI workflow pushed and its run status determined" is therefore **half satisfied**: the workflow is
   pushed and its syntax validated, but its first run must be confirmed by the repository owner (or by
   granting the session's token Actions read access). No substitute evidence is claimed.
2. **Windows golden baseline not promoted yet.** The authoritative baseline comes from the `windows-build`
   job's uploaded renders; until those are reviewed and promoted, the golden tests *skip* on Windows with an
   explicit instruction (`python tools/promote_goldens.py`) instead of passing silently. The Linux baseline
   is committed.
3. **Installer hardening and clean-machine testing are Phase 11 by design** — the Phase 1 NSIS script
   delivers the per-user skeleton (documented in `packaging/README.md`); the optional all-users mode,
   installer-detail polish and the clean-machine checklist are Phase 11 items, not silently dropped.
4. **Dark theme is not implemented** because the specification requires a premium light clinical theme and
   does not ask for a dark mode; this is stated here rather than shipped as a half-working toggle.

## 5. Acceptance gate

| Gate item | Status |
|---|---|
| Shell renders with goldens | **Pass** — 13 committed Linux goldens, promotion workflow documented and tested (tamper test fails the gate) |
| App starts and opens an empty initialised DB | **Pass** — `--check` smoke test, acceptance test, and UI shell tests on an initialised database |
| CI workflow pushed and its run status determined | **Partial** — pushed and validated; run status requires the owner's confirmation because the token cannot read Actions (see §4.1) |
| Lint/type/test gates green | **Pass** — ruff, format, strict mypy, secret scan, 302 tests |

**Phase 1 is not declared fully complete**: one gate item depends on evidence this environment cannot
produce, and the rule for this project is that a phase closes only when its criteria pass. The remaining
step is for the repository owner to confirm the first `CI` workflow run (or grant Actions access) — the
code itself is ready for that run: pushing the branch triggers `quality`, `tests-linux` and
`windows-build`.

## 6. Files and areas changed

* Added: `pyproject.toml`; `src/dentivapro/**` (core, data, domain, services, ui + assets); `tests/**`;
  `tools/**`; `packaging/**`; `.github/workflows/ci.yml`; `docs/phase-reports/phase-1-report.md`.
* Updated: `docs/requirements-traceability.md` (17 rows advanced: R-06 and R-93 done, the rest in progress).
* Unchanged: Phase 0 architecture documents, licences, acceptance matrix, phase plan.
* Committed goldens: `tests/ui/goldens/linux/` (13 PNG + 13 fingerprint JSON, 2.6 MB); renders are written
  to git-ignored `tests/ui/artifacts/screens/` for review.

## 7. Next phase (after approval)

Phase 2 — database, domain model, security, authentication, RBAC, audit and activation (Argon2id,
sessions, auto-lock foundation, permission enforcement in services, derived activation verification with
the literal never stored). Work does not start until the owner says **Continue**.
