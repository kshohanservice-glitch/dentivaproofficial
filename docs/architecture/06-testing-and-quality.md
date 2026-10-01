# Dentiva Pro — Testing, Quality Gates and Verification Strategy (Phase 0)

The rule this project follows: **a feature is complete only when its data model, business logic, UI,
error handling, permissions, persistence, audit behaviour, tests and integration behaviour all work.**

---

## 1. Test levels

| Level | Location | Scope | Tooling |
|---|---|---|---|
| Unit | `tests/unit/` | Money/Decimal arithmetic, date handling, code generation, validators, similarity matching, permission resolution, activation derivation (synthetic verifier), template CSS lint, settings registry | pytest |
| Integration | `tests/integration/` | Repositories against a real SQLite file: constraints, FKs, transactions, rollbacks, concurrency, pagination, snapshots, audit emission, migrations | pytest + temp DB |
| Service/business | `tests/services/` | Workflow rules: invoice + lines + payment consistency, void/reversal, stock ledger, appointment conflicts, duplicate detection, queue transitions, prescription finalisation | pytest |
| Security | `tests/security/` | Password hashing policy, lockout/back-off, session invalidation, permission-denial matrix per role, read-model guards, audit immutability, path traversal, zip slip, secret scanning | pytest + spy connection |
| Printing | `tests/printing/` | Layout matrix, PDF rendering, Bengali glyph presence, determinism, failure modes | Qt offscreen + pypdf/Pillow |
| UI (render/interaction) | `tests/ui/` | Golden images at multiple DPIs, layout invariants, keyboard traversal, state coverage, permission-driven UI | pytest-qt + offscreen QPA |
| Performance | `tests/perf/` | Query budgets, list/dashboard timings, startup time, memory growth, large-dataset stress | pytest + seeded 50 k patient DB |
| Acceptance (E2E) | `tests/acceptance/` | Full clinic workflows driven through services *and* through the real UI where it matters, mapping 1:1 to the acceptance matrix | pytest(-qt) |
| Packaging | `packaging/tests/` + CI | Bundle contents, no dev dependencies, no secrets, EXE launch smoke, uninstall/reinstall behaviour | GitHub Actions (windows-latest) |

## 2. Environments

- **Local (this sandbox):** Linux + offscreen Qt. Runs unit, integration, service, security, printing
  (PDF/PNG artefacts), UI goldens (Linux baseline), performance. Bengali fonts are bundled, so shaping is
  verified here.
- **CI — `ubuntu-latest`:** fast gates (lint, type check, unit/integration/security/printing/perf, coverage).
- **CI — `windows-latest`:** authoritative UI goldens (Windows font/rasterisation baseline), EXE build via
  PyInstaller, packaged-bundle smoke test (launch offscreen, create DB, render prescription PDF, open
  existing DB, verify no missing DLLs), NSIS installer build, installer smoke (silent install → launch →
  uninstall), artifact upload. **The released installer is produced only here.**
- **Clean Windows machine (manual checklist, Phase 11):** real install, activation, first-run setup,
  restart, printing on a physical printer/PDF, uninstall/reinstall, DPI change.

## 3. Test data strategy

- Deterministic fixtures via seeded generators (`tools/seed.py --patients 50000 --years 3 --seed 42`) that
  create realistic Bangladeshi names (Latin + Bengali), phone numbers, addresses, treatments, medicines,
  invoices, payments, inventory and attachments.
- No sample/demo data is ever shipped in production: seeding is a development/test-only command and the
  production build contains no data files (an empty database is initialised at first run; verified by a
  packaging test that asserts the bundle contains no `.db`).
- Golden/UI fixtures use their own small deterministic dataset so goldens stay stable.

## 4. Quality gates (CI, all mandatory)

1. `ruff check` + `ruff format --check` (lint/format) — zero warnings in production code.
2. `mypy` on `src/` (strict on `core/`, `services/`, `data/`) — no errors.
3. Full pytest suite, coverage ≥ 85 % statements / ≥ 75 % branches on `src/dentivapro` (the number is
   enforced, not aspirational), with per-area minimums (services, security, money ≥ 90 %).
4. Security suite green, including the permission matrix and secret scan of `dist/`.
5. Printing matrix green with PDF artifacts uploaded.
6. Performance budgets green (`tests/perf/test_budgets.py` asserts documented thresholds).
7. Custom static gates: no bare `except: pass`; no raw SQL string concatenation in `src/`; no raw hex
   colours/pixel paddings outside `ui/design/`; no `TODO/FIXME/XXX/HACK` markers; no `print()` in
   production code (logging only); no `placeholder`, `coming soon`, `mock`, `dummy`, `lorem`, `fake`
   identifiers in production code (case-insensitive scan with an allow-list for legitimate words such as
   "placeholder text" in UI widgets); no secrets in the tree.
8. Windows job: goldens, bundle smoke, installer build, installer smoke.

A failing gate blocks the phase. Gates are implemented as scripts under `tools/qa/` so a developer can run
the exact same checks locally (documented in `docs/development.md`).

## 5. Requirement → test traceability

`docs/requirements-traceability.md` holds one row per requirement group from the master specification with:
requirement id, statement (short), design document section, implementing module(s), test file(s)/test ids,
phase, and status. `docs/acceptance-test-matrix.md` expands the acceptance items into executable test
cases with expected results. Both files are updated in every phase; a CI script
(`tools/qa/check_traceability.py`) fails the build if a requirement row lacks a test id or a test id does
not exist in the suite.

## 6. Manual verification where automation cannot reach

Documented checklists with an evidence slot (screenshot/log path) for: real printer/media behaviour,
touch/pen input on Windows tablets, Bluetooth printer pairing, Windows SmartScreen behaviour of the
unsigned installer, low-disk/storage-full behaviour on a real drive, USB-drive removal during backup,
multi-monitor and 175/200 % DPI appearance, and the clean-machine sequence in Phase 11.

## 7. Regression discipline

- Every defect found in any phase gets: a failing test first, the fix, then the test kept forever
  (`tests/regression/test_<defect-id>.py` with the phase and defect description in a docstring).
- Phase reports list defects found and fixed with their test ids.
- The full suite (including UI goldens and performance budgets) is run at every phase boundary, and the
  Phase 11/12 runs are on the frozen release candidate only.

## 8. Performance budgets (enforced)

| Operation | Budget |
|---|---|
| App cold start to login screen (bundled, warm OS cache) | ≤ 3.0 s |
| Login (Argon2id verify included) | ≤ 1.5 s |
| Patient list first page (50 rows) from 50 k patients | ≤ 300 ms |
| Patient search keystroke → results | ≤ 250 ms (debounced 200 ms) |
| Patient profile open (overview + counts) | ≤ 500 ms |
| Visit history tab (200 visits) | ≤ 600 ms |
| Dashboard (all widgets, 50 k patient dataset) | ≤ 1.5 s |
| Prescription preview render (2 pages) | ≤ 1.0 s |
| Invoice save + reprint render | ≤ 800 ms |
| Payment post (incl. invoice cache update + audit) | ≤ 200 ms |
| Inventory movement post | ≤ 150 ms |
| Backup of 500 MB data (incl. verification) | ≤ 90 s (progress UI responsive) |
| Restore of 500 MB backup | ≤ 120 s |
| 1 M-row audit/report aggregate query | ≤ 2.0 s |
| Peak RSS with 50 k-patient dataset after full navigation pass | ≤ 700 MB |

## 9. Definition of done per phase

A phase is done only when: its scope is implemented; all its acceptance tests pass; no critical defect is
open; the traceability matrix is updated; static gates pass; the phase report states explicitly what was
implemented, tested, failed, fixed, remains, and whether the phase's acceptance criteria passed; and the
user has said *Continue*.

## 10. Release-candidate rules (Phases 11–12)

The RC is built once from the phase-complete commit; any change after that invalidates the RC and requires
a rebuild plus a full re-run of the acceptance matrix. No feature work is allowed during RC validation.
