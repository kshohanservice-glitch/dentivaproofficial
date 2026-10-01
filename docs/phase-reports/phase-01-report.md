# Phase 1 Report — Product Discovery, Requirements Freeze and Technical Planning

**Phase:** 1 of 18 — Discovery, requirements freeze and technical planning
**Date:** 2026-10-01
**Branch:** `arena/01a0f67e-dentivaproofficial` (session branch; base `main` @ `bd4dc4c`)
**Status: COMPLETE — the plan is frozen and the traceability baseline exists. No Phase 1 work is outstanding.**

> **Execution note.** The product's Phase 1 (planning) and Phase 2 (engineering foundation) both exist in
> this repository: discovery and the architecture plan were produced first, and foundation work was then
> started in a previous session on a sibling branch (`arena/01a0f649-…`). This session re-verified the
> repository state from scratch, took over that work on the session branch, finished the unfinished parts
> of the foundation, and re-aligned the plan to the specification's 18 phases. The foundation itself is
> reported separately in `phase-02-report.md`. Nothing in this report claims work that is not in the
> repository.

---

## 1. What was inspected (not assumed)

| Item | Finding |
|---|---|
| Repository contents | `main` contained a single commit `bd4dc4c` with only `README.md`. No code, schema, build files, CI or docs. |
| Branches | `main` @ `bd4dc4c`; session branch `arena/01a0f67e-…` (initially identical to `main`); a sibling session branch `arena/01a0f649-…` @ `2f3386d` carrying planning + foundation work. |
| Open pull requests | PR #1 (`Phase 0 — Discovery…`) open on the sibling branch, **not merged**. The agent never merges pull requests. |
| GitHub capability | Push, fetch, PR/issue/run/annotation reads work. `gh` log download is blocked (the signed URL host `*.blob.core.windows.net` is not reachable from this sandbox), so failure evidence is obtained from step annotations and from diagnostics the workflow itself publishes. |
| Local environment | Debian 12 sandbox, 2 vCPU, 3.8 GB RAM, 20 GB disk, Python 3.11.2 (+ a 3.11 venv for the project), no display, no Windows, no Wine, no NSIS; `sudo` present but no apt mirror. |
| Repository files at hand-over | 220 files: `pyproject.toml`, `src/dentivapro/**`, `tests/**` (302 tests), `tools/**`, `packaging/**`, `.github/workflows/ci.yml`, and the full `docs/` set. |
| CI at hand-over | Every run on the sibling branch had failed. The most recent failures were: the Windows bundle self-check (fixed by the sibling session in `2f3386d`), then the NSIS installer step. |
| Local verification before any new work | Full suite executed on this machine: **309 passed**, `ruff` clean, `ruff format --check` clean, strict `mypy` clean (62 files), secret scan clean (220 files), `python -m dentivapro --check` reporting a healthy initialised database. |

## 2. Requirements baseline

* **120 requirement groups** extracted from the specification, each with design reference, implementing
  module, verification method, target phase and status: `docs/requirements-traceability.md`.
* **171 acceptance items** (AT-001…AT-171), including automated, performance-budgeted and manual
  clean-machine items: `docs/acceptance-test-matrix.md`.
* **18 execution phases** matching the specification one-for-one: `docs/phase-plan.md`.
* Coverage spot-checked against the specification's own sections (first-run experience, shell and
  navigation, UI system, responsive/High-DPI, icon/branding, patients, visits, timeline, dental chart,
  treatment catalogue, prescriptions, clinical vocabulary, prescription document design, printing and
  paper profiles, invoices, payments, financial history, inventory, accounting, staff/users, RBAC,
  authentication, activation, backup/restore, settings, destructive safeguards, global search,
  appointments, queue, notifications, dashboard, attachments, referrals, audit, data model, financial and
  medical integrity, Bengali/Unicode, print preview, shortcuts, error handling, logging, performance,
  states, import/export, retention/deletion, security, dependency/licence audit, GitHub workflow,
  installer, clean-machine validation, stress testing, end-to-end acceptance, documentation).

## 3. Environment probes that shaped the architecture (all executed)

| Probe | Result | Consequence |
|---|---|---|
| PySide6 6.11.2 install and offscreen start | Works (with loader-only stubs for four desktop libraries on this bare container) | Qt is the UI and print stack, and it is testable headlessly here |
| Bengali rendering | Boxes without a Bengali font; perfect shaping of conjuncts, ৳ and Bengali digits with bundled Noto Sans Bengali | Fonts must be bundled and validated in CI, not assumed present |
| Offline PDF | `QPdfWriter` produced a valid A5 PDF containing Bengali text | Prescription/invoice PDF output is local, free and testable |
| SQLite capability | 3.40.1 with FTS5, column metadata and DBSTAT | Schema plan is compatible with the Windows runtime |
| Performance smoke | 100 000 patients inserted in 0.89 s; indexed prefix search 0.12 ms; 50-row page query 9.4 ms; 20 000-row Qt table renders in 0.04 s | The documented performance budgets are realistic; no artificial record caps |
| Argon2id cost | m=64 MiB, t=3, p=2 → 76 ms per hash | Strong password hashing is practical interactively |
| Windows wheels | Resolved for the whole dependency set (`pip download --platform win_amd64 --python-version 3.12`) | The dependency closure is proven for the target platform before coding |
| Font licences | Inter and Noto Sans Bengali under OFL-1.1, vendored with their licences | Redistribution is lawful and offline |
| PyInstaller locally | Cannot link (sandbox Python has no shared library) | The `.exe` and installer are produced by Windows CI only — never faked locally |
| Electron/Chromium route | Blocked (release CDN unreachable) and heavier | Rejected on evidence, not preference |

## 4. Technology decisions (frozen)

1. **Python 3.12 + PySide6 (Qt 6) Widgets** — proven offline print subsystem (preview, printer
   selection, paper sizes, PDF), verified Bengali shaping, deterministic headless rendering for automated
   UI verification, complete Windows wheel set. QML rejected (data-dense tables and print fidelity are
   stronger in QtWidgets); Electron rejected (unreachable toolchain, memory, no benefit).
2. **SQLite (WAL) with explicit SQL, a repository layer and unit of work** — zero-install ACID storage,
   `VACUUM INTO` backups, integrity checks. An ORM was rejected: money, audit and transaction semantics
   require explicit control.
3. **Decimal money persisted as integer paisa** — exact BDT accounting; binary floats are rejected
   outright by the domain type. Quantities are stored as thousandths.
4. **RBAC enforced in services and read-model guards**, with a permission matrix that proves denial
   before any SQL executes ("hiding is not security").
5. **Append-only audit log** enforced by database triggers, with before/after payloads for sensitive
   changes.
6. **Derived, non-plaintext offline activation** (PBKDF2-HMAC-SHA256 verifier split into obfuscated
   fragments, HMAC-protected state file, per-attempt delay, secret scanning in CI) with the limitation
   stated honestly: a purely local check cannot be mathematically secret.
7. **Qt print pipeline with millimetre-accurate profiles** (A4/A5/A6/Letter/80 mm/58 mm/custom), one
   render path for preview, printer and PDF, and a fixed-height signature block that printed content
   never enters.
8. **Validated `.dprobackup` containers** (database snapshot + attachments + hashed manifest), pre-restore
   safety backup, staged verification, atomic swap with automatic rollback, scheduled backups at
   7/15/30 days, all offline.
9. **PyInstaller onedir + NSIS** — replaceable Qt DLLs (LGPL compliance), fast start, per-user install
   without an administrator prompt, silent install for CI, uninstall that never deletes clinic data
   silently.
10. **GitHub Actions is the release path** — Linux quality/test gates plus a Windows job that builds the
    bundle, audits it, launches it, builds the installer, installs it silently, verifies database
    initialisation and uninstalls. `dist/` remains the documented fallback if Release publication is
    unavailable.

Rejected alternatives are recorded with reasons in `docs/architecture/00-architecture-overview.md`.

## 5. Deliverables

| Area | Files |
|---|---|
| Architecture | `docs/architecture/00-architecture-overview.md`, `01-domain-and-data-model.md`, `02-security-and-rbac.md`, `03-ui-and-design-system.md`, `04-printing-and-documents.md`, `05-backup-and-restore.md` |
| Quality, build, dependencies | `docs/architecture/06-testing-and-quality.md`, `07-build-installer-ci-release.md`, `08-dependency-license-audit.md` |
| Baseline | `docs/requirements-traceability.md` (120 rows), `docs/acceptance-test-matrix.md` (171 items), `docs/phase-plan.md` (18 phases), `docs/environment-and-limitations.md` |
| Legal | `LICENSE`, `THIRD_PARTY_NOTICES.md`, vendored OFL licences |

## 6. Corrections made to the plan during this session

| # | Issue found | Resolution |
|---|---|---|
| 1-1 | The plan used a private 13-phase numbering (0–12) instead of the specification's 18 phases | `docs/phase-plan.md` rewritten as the specification's 18 phases, with the completed work mapped onto Phases 1–2 and a numbering note; all phase references in source, docs and packaging renumbered; reports renamed to `phase-01-report.md` / `phase-02-report.md` |
| 1-2 | The traceability matrix and testing documentation referenced static gates (`tools/qa/*`) that did not exist | The four gates were implemented, wired into CI, tested, and the documentation corrected to describe their real behaviour (including `--release` mode) |
| 1-3 | `docs/architecture/08…` claimed pinned versions would land in `requirements.lock`, which does not exist | Documentation corrected: every runtime dependency is pinned in `pyproject.toml` |
| 1-4 | Phase numbers shown to clinic users in the shell ("scheduled for Phase 7") did not match the plan the owner reads | UI strings, shortcut notes and permission comments renumbered; goldens re-promoted |

## 7. Phase 1 acceptance gate

| Gate item | Status |
|---|---|
| Repository and environment inspected, capabilities proven by executed probes | **Pass** (§1, §3) |
| Requirements frozen with a traceability baseline | **Pass** — 120 rows, structurally validated by `tools/qa/check_traceability.py` on every push |
| Architecture, data model, security, UI, printing, backup, testing, CI and release plans defined | **Pass** (`docs/architecture/00–08`) |
| Technology decisions recorded with justification and rejected alternatives | **Pass** (§4) |
| Phase plan aligned with the specification's 18 phases | **Pass** (§6, `docs/phase-plan.md`) |
| No major application feature built in this phase | **Pass** — Phase 1 produced documents and the engineering baseline only |

## 8. Honest limitations carried forward

1. **No Windows in the development sandbox.** Everything Windows-specific (EXE, installer, clean-machine
   behaviour) is verified by CI and by the manual checklist in Phase 17; local Windows claims are never
   made.
2. **Activation secrecy has a documented ceiling.** A local fixed secret can be reverse engineered by a
   sufficiently determined attacker with control of the machine; the design raises the cost and keeps the
   literal out of the source, and says so plainly (`docs/architecture/02-security-and-rbac.md` §7).
3. **The installer is unsigned** (no certificate exists). Windows SmartScreen will warn; this must be
   stated in the release notes rather than hidden.
4. **Thermal printing goes through the Windows driver.** ESC/POS-only devices with no Windows driver are
   not driven directly in the baseline; this is documented as a limitation, and printer findings from the
   manual checklist feed the Phase 14 hardening.
5. **The Windows golden baseline is not promoted yet.** Linux fingerprints are committed; Windows
   renders are produced and uploaded by CI for the owner to review and promote (§`phase-02-report.md`).
6. **CI evidence depends on the repository's Actions settings.** Runs and annotations are readable here;
   raw log download is not, so the workflow publishes failure output itself.

## 9. What happens next

Phase 2 (repository, engineering foundation and design system) is already in the repository and is
reported in `phase-02-report.md`. The next phase that has not been started is **Phase 3 — Database,
Domain Model, Security and RBAC**, which begins only when the owner says **Continue**.

**Phase 1 is complete. Awaiting "Continue" for Phase 3.**
