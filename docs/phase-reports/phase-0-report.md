# Phase 0 Report — Discovery, Environment Verification and End-to-End Architecture Plan

**Phase:** 0 (Discovery, repository inspection, architecture planning)
**Date:** 2026-10-01
**Branch:** `arena/01a0f649-dentivaproofficial` (from `main` @ `bd4dc4c`)
**Status: COMPLETE — awaiting the user's explicit "Continue" before Phase 1**

---

## 1. What was inspected

| Item | Finding |
|---|---|
| Repository contents | Only `README.md` (21 bytes: `# dentivaproofficial`) and a single commit `bd4dc4c Initial commit`. No code, no schema, no build files, no CI, no docs. |
| Branches / remotes | `main` and the session branch `arena/01a0f649-dentivaproofficial`; `origin` = `github.com/kshohanservice-glitch/dentivaproofficial` (public, default branch `main`). No PRs, no workflows, no releases exist yet. |
| GitHub capability from this environment | Push/fetch and `gh` read operations work (token is a GitHub App installation token: `arena-ai-coding-agent[bot]`). The repository as seen by the API reports `pull:false` (PR creation must be verified at the time it is attempted). `gh api .../actions/permissions` returns **403 Resource not accessible by integration** — Actions scope is not granted to this token. |
| Local environment | Linux (Debian 12) sandbox, 2 vCPU, 3.8 GB RAM, 20 GB disk, Python 3.11.2, Node 22, gcc/g++, `sudo` available but the apt mirror is unreachable (`deb.debian.org` connection failure). No `wine`, no `.NET` SDK, no browser. |
| Network egress allowlist | Reachable: `registry.npmjs.org`, `pypi.org`, `github.com`, `api.github.com`, `codeload.github.com`. Blocked: `objects.githubusercontent.com` (GitHub release assets), `nodejs.org`, `deb.debian.org`, `registry.npmmirror.com`, `cdn.jsdelivr.net`, `unpkg.com`, `storage.googleapis.com`, `api.nuget.org`, `packages.microsoft.com`, Playwright CDNs. |

## 2. Environment probes that shaped the architecture (all executed, not assumed)

| Probe | Result | Architectural consequence |
|---|---|---|
| PySide6 (Qt 6.11.2) install from PyPI | Installed successfully; required four tiny stub shared libraries to satisfy the sandbox's missing desktop libraries for headless use | Qt is the UI/print stack; it is fully testable here (offscreen rendering + PDF) |
| Headless Qt render + Bengali text | Rendered PNG before/after bundling fonts: **without** a Bengali font the text showed boxes; **with** Noto Sans Bengali every conjunct (ক্ষ জ্ঞ ন্ত ষ্ট র্ম ট্র দ্ব প্র ঞ্চ হ্ম), the ৳ sign and Bengali digits rendered correctly | Fonts must be bundled (they will be), and Bengali requirements are provably achievable |
| Offline PDF via `QPdfWriter` | Valid A5 PDF (13 KB) with Bengali table content | PDF generation is local/free and testable here |
| SQLite capability | Python 3.11 ships SQLite 3.40.1; `ENABLE_FTS5`, `ENABLE_COLUMN_METADATA`, `ENABLE_DBSTAT_VTAB` present | Schema plan is compatible with the Windows runtime (Python 3.12 → SQLite ≥ 3.37) |
| Performance smoke | 100 000 patient rows inserted in 0.89 s; indexed prefix search 0.12 ms; 50-row page query 9.4 ms; `COUNT(*)` 0.59 ms; Qt table with 20 000 rows renders in 0.04 s | The documented performance budgets are realistic; no artificial patient cap is needed |
| Argon2id cost | m=64 MiB, t=3, p=2 → 76 ms per hash | Strong password hashing is practical for interactive login |
| Windows wheel availability | `pip download --platform win_amd64 --python-version 3.12` succeeded for PySide6-Essentials 6.11.2, shiboken6, argon2-cffi 25.1.0 + bindings 26.1.0, cryptography 50.0.2, pyinstaller 6.22.3, platformdirs 4.12.2, segno 1.6.6, pytest 9.1.1, pytest-qt 4.5.0, ruff, mypy, pypdf, Pillow | The full production/test dependency closure is validated for the target platform *before* writing code |
| Font acquisition | Both Inter and Noto Sans Bengali plus their OFL-1.1 licences fetched through the GitHub API and vendored into `docs/licenses/` | Legal, reproducible font bundling |
| PyInstaller | Analysis runs on Linux; fails only because the sandbox Python lacks a shared library (`libpython3.11.so`) | Local EXE bundling is impossible here; the bundle is a Windows-CI responsibility |
| Electron/Chromium route | Blocked: the Electron installer downloads from `objects.githubusercontent.com`, which is unreachable, and no browser binary exists | Electron/WebView stacks were rejected on evidence, not preference |

## 3. Architecture decisions (summary with rationale; full detail in `docs/architecture/`)

1. **Python 3.12 + PySide6 (Qt 6) Widgets** — the only stack that provides a proven offline print subsystem
   (preview, printers, paper sizes, PDF), verified Bengali shaping, deterministic headless rendering for
   automated UI verification, and a complete Windows wheel set reachable from PyPI. Electron was blocked by
   the environment and is heavier; .NET/NuGet is unreachable; QML was rejected because data-dense tables and
   print fidelity are stronger in QtWidgets.
2. **SQLite (WAL) with explicit SQL, a repository layer and a unit of work** — zero-install ACID storage
   with `VACUUM INTO` backups and integrity checks; an ORM was rejected because the money, audit and
   transaction semantics here demand explicit control.
3. **Decimal money persisted as integer paisa** — exact BDT accounting, never binary floats; quantities as
   thousandths to avoid float drift on fractional units.
4. **Server-side RBAC enforced in services and read-model guards**, with a "hiding is not security" test
   matrix proving denial before any SQL executes.
5. **Append-only audit log** enforced by SQLite triggers, with before/after payloads for sensitive changes.
6. **Derived, non-plaintext offline activation** (PBKDF2-HMAC-SHA256 verifier split into obfuscated
   fragments, HMAC-protected state file, per-attempt delay, secret scanning in CI) with the honest
   documented limitation that a purely local check cannot be mathematically secret.
7. **Qt print pipeline with mm-accurate profiles** (A4/A5/A6/Letter/80 mm/58 mm/custom), a single render
   path for preview/printer/PDF, fixed-height signature block, explicit printer-capability failure handling.
8. **Validated `.dprobackup` containers** (DB snapshot + attachments + hashed manifest), pre-restore safety
   backup, staged verification and atomic swap with automatic rollback; scheduled backups at 7/15/30 days.
9. **PyInstaller onedir + NSIS** — DLLs stay replaceable (LGPL compliance), fast start, silent install
   support, clean uninstall with explicit data-retention policy, and honest unsigned-release reporting when
   no certificate exists.
10. **GitHub Actions is the release path**: Linux quality gates + Windows bundle/installer build and smoke
    tests; `dist/` remains the documented fallback if Release publication is unavailable.

## 4. Deliverables produced in Phase 0

| File | Purpose |
|---|---|
| `docs/architecture/00-architecture-overview.md` | Environment findings, decision table with rejections, layered architecture, runtime topology, config model, logging, localization/currency, performance, risks |
| `docs/architecture/01-domain-and-data-model.md` | Full entity catalogue (system, people, patients/clinical, appointments/queue, billing/accounting, inventory, audit/notifications), identifier strategy, index plan, integrity/deletion/retention rules, attachment storage, read models |
| `docs/architecture/02-security-and-rbac.md` | Threat model, password policy, sessions/auto-lock/lockout, permission catalogue and seeded role matrix, audit actions, file-system security, activation design and test strategy |
| `docs/architecture/03-ui-and-design-system.md` | Design tokens (colour/typography/spacing/radii/elevation/motion/metrics), shell layout, routing, component inventory, mandatory states, keyboard contract, UI defect checklist, automated UI verification |
| `docs/architecture/04-printing-and-documents.md` | Engine decision, document model, print profiles, prescription/invoice/thermal/report templates, pagination and signature guarantees, failure handling, determinism, test matrix |
| `docs/architecture/05-backup-and-restore.md` | Container format and manifest, inclusion policy, failure-safe creation, validated atomic restore with pre-restore backup, scheduling, integrity tooling, destructive-action protection |
| `docs/architecture/06-testing-and-quality.md` | Test levels, environments, data strategy, CI quality gates, performance budgets, manual verification, regression discipline, definition of done |
| `docs/architecture/07-build-installer-ci-release.md` | Versioning, repository structure, build pipeline, PyInstaller/NSIS details, signing policy, workflows, release and rollback strategy, operational documentation list |
| `docs/architecture/08-dependency-license-audit.md` | Dependency inventory with licences and obligations, paid-service audit (zero recurring cost), licensing checklist, third-party re-use policy |
| `docs/requirements-traceability.md` | 120 requirement groups → design → implementation → verification → phase → status |
| `docs/acceptance-test-matrix.md` | AT-001…AT-171 with steps and expected results (automated, performance-budgeted, manual) |
| `docs/phase-plan.md` | The 13 phases with deliverables and acceptance gates |
| `docs/environment-and-limitations.md` | Verified capabilities, verified limitations, sandbox-only scaffolding policy |
| `docs/licenses/OFL-1.1-*.txt` | Vendored font licences |
| `README.md`, `CHANGELOG.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `CONTRIBUTING.md`, `.gitignore`, `.gitattributes` | Repository scaffolding and legal/notice foundations |

## 5. Tests executed in Phase 0

Phase 0 has no product code, so its verification consists of environment and feasibility probes (all
executed in this session, results in §2): Qt headless startup, Bengali rendering comparison, PDF generation,
SQLite capability and performance benchmark, Argon2id timing, Windows wheel resolution for the full
dependency set, font/licence acquisition, PyInstaller capability, GitHub capability, and network reachability
probing. No product test suite exists yet (created in Phase 1).

## 6. Defects found and fixed in Phase 0

| # | Issue found | Resolution |
|---|---|---|
| 0-1 | Bengali text rendered as boxes with the base sandbox fonts | Bundled Noto Sans Bengali; verified correct shaping of conjuncts, ৳ and Bengali digits. Documented as a product requirement (bundle fonts, block printing if a font fails to load) |
| 0-2 | Qt would not start headless (missing `libGL`, `libEGL`, `libxkbcommon`, `libdbus`) | Created dev-sandbox stub shared libraries (loader-index-aligned and version-script aligned where required) used only via `LD_LIBRARY_PATH`; excluded from Git and provably absent from any distribution |
| 0-3 | PyInstaller cannot bundle with the sandbox Python (no shared `libpython`) | Moved bundling to the Windows CI job; local work focuses on the spec file, tests and non-EXE artifacts |
| 0-4 | Electron/Chromium route infeasible (release CDN blocked) | Architecture chooses Python/Qt; documented as evidence-based rejection |
| 0-5 | GitHub token lacks Actions scope → CI run status may be unreadable | Phase 1 will push a minimal workflow and report exactly what is observable; release reporting will distinguish CI-produced artifacts from locally verified ones |

## 7. Known limitations carried forward

1. No Windows execution environment here → EXE/installer/clean-machine validation happens in GitHub Actions
   `windows-latest` and in the Phase 11 manual checklist.
2. No physical printers → print correctness is proven by PDF/PNG rendering across the full paper matrix;
   real-device behaviour is a manual checklist item.
3. Offline activation cannot be mathematically secret → documented honestly; controls reduce extractability
   and detect tampering.
4. GitHub Actions availability for this repository is unverified (token scope) → Phase 1 verifies and
   reports; `dist/` is the documented fallback.

## 8. Phase 0 acceptance criteria

| Criterion | Result |
|---|---|
| Repository and environment inspected with evidence | **PASS** |
| Every selected production dependency validated as free-of-cost and Windows-installable | **PASS** |
| Application stack, database, UI, security, RBAC, printing, backup, activation, testing, installer, CI and release strategies decided and justified | **PASS** |
| Requirements traceability and acceptance matrices created | **PASS** |
| Phase plan with gates defined | **PASS** |
| No production code or implementation started | **PASS** (documentation and repository scaffolding only) |
| Report delivered and awaiting explicit user approval | **PASS** (this document) |

## 9. Next phase (on "Continue")

**Phase 1 — Foundation, project structure, design system and Windows shell:** repository structure, build
configuration (pyproject, ruff, mypy, pytest), package skeleton, design tokens and component primitives,
application shell (header + collapsible sidebar + router + shortcuts), logging and error-boundary
foundation, configuration/settings registry, database bootstrap, initial PyInstaller/NSIS packaging skeleton,
the first CI workflows (including the attempt to verify Actions behaviour), and the first tests with a
production-like build — followed by a Phase 1 report and a stop.

**No implementation work will begin until the user says "Continue".**
