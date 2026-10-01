# Dentiva Pro — System Architecture Overview (Phase 0)

**Product:** Dentiva Pro — offline-first dental clinic management for Bangladesh
**Target platform:** Windows 10 (1809+) / Windows 11, x64
**Version target:** 1.0.0 (deterministic, final release line)
**Document status:** Phase 0 baseline — architecture frozen for implementation unless a defect forces change

---

## 1. Product scope in one paragraph

Dentiva Pro is a single-machine, fully offline Windows desktop application used at a dental clinic's
front desk and operatory PC. It manages the complete clinic loop: first-run clinic/dentist setup,
secure multi-user authentication with granular RBAC, practically unlimited patients with longitudinal
clinical + financial history, appointments and queue, clinical visits with an adult/pediatric dental
chart, a treatment catalog, multi-medicine prescriptions with premium print/PDF output (A4/A5/thermal),
invoicing with multi-payment financial history, inventory with expiry and low-stock control,
income/expense accounting with period reports, patient attachments, advanced global search,
a notification centre, and verified backup/restore with pre-restore safety backups.

Nothing in the product requires the internet, a paid API, a cloud service or a subscription after
installation. A fixed one-time offline activation is the only gating mechanism.

---

## 2. Environment findings that shaped the decisions

| Finding | Evidence | Consequence |
|---|---|---|
| Repository was effectively empty (21-byte README, 1 commit) | `git log` / `ls` | No legacy constraints; clean architecture from scratch |
| Sandbox is **Linux (Debian 12)**, 2 vCPU, 4 GB RAM, 20 GB disk | `uname`, `free`, `df` | No native Windows test execution here → Windows validation must run in GitHub Actions `windows-latest` |
| Sandbox egress allowlist: npm registry, PyPI, GitHub API/web OK; **GitHub release CDN, apt, nodejs.org, CDN mirrors blocked** | 20-host curl probe | Cannot download Electron/Chromium/NSIS locally; cannot `apt install wine`; Windows-only toolchains are unavailable locally |
| No `wine`, no `.NET` SDK reachable (NuGet blocked) | `which wine`, `dotnet`, `api.nuget.org → 000` | .NET/WPF and Wine-based verification are not viable here |
| **PySide6 (Qt 6.11) installs from PyPI and runs headless** (`offscreen` platform) after supplying 4 stub shared libraries for the sandbox's missing desktop libs | `qtprobe.py` → rendered PNG + PDF | Qt is fully testable in this sandbox, including pixel-accurate UI snapshots and PDF output |
| Unknown Bengali text rendered as boxes (no Bengali font in the base image); bundling **Noto Sans Bengali** fixed shaping completely (conjuncts ক্ষ জ্ঞ ন্ত ষ্ট র্ম ট্র দ্ব প্র ঞ্চ হ্ম, ৳ sign, Bengali digits) | `/tmp/qtprobe2.png` | Bengali correctness is proven feasible offline by bundling fonts |
| Performance: 100 000 patient rows inserted in 0.89 s; indexed prefix search 0.12 ms; paged 50-row query 9.4 ms; Qt table with 20 000 rows renders in 0.04 s | `perfprobe.py` | SQLite + Qt model/view + keyset pagination meets large-dataset requirements |
| All production wheels exist for **win_amd64 / cp312**: PySide6-Essentials, shiboken6, argon2-cffi(+bindings), cryptography, pyinstaller, platformdirs, segno | `pip download --platform win_amd64` | Windows dependency closure is validated before writing code |
| Argon2id at m=64 MiB, t=3, p=2 → 76 ms/hash | `argon2` probe | Strong password hashing is practical for interactive login |
| GitHub token is a **repo-scoped GitHub App token** without Actions API scope; pushes and PRs work | `gh api …/actions/permissions → 403`, `gh pr list → OK` | CI can be authored and pushed; run-status/log retrieval may be unavailable — must be verified in Phase 1 and reported honestly |
| PyInstaller cannot bundle from the sandbox Python (no shared `libpython`) | `pyinstaller build.spec` error | Local packaging is Linux-only irrelevant; the real bundle/installer is built and smoke-tested on `windows-latest` |

Full detail and mitigations: `docs/environment-and-limitations.md`.

---

## 3. Technology decisions

Every decision below is justified against: offline reliability, Windows compatibility, long-term
maintainability, printing reliability, security, performance, packaging/installer reliability,
licensing, and the specific requirements of this product.

### 3.1 Application stack — decision table

| Layer | Choice | Why this and not the alternatives |
|---|---|---|
| Language | **Python 3.12** (bundled by PyInstaller) | Mature stdlib for SQLite/`Decimal`/`secrets`, first-class Qt bindings, no runtime install needed for the end user, excellent long-term maintainability. |
| UI toolkit | **PySide6 (Qt 6.11, QtWidgets)** | Qt ships its own print subsystem (`QPrinter`, `QPrintPreviewWidget`, `QPdfWriter`) that is the single most important technical requirement here; strong high-DPI support; a native Windows look when needed; **LGPLv3** (free for commercial redistribution with obligations, §8). Alternative **WPF/.NET** was rejected: no .NET SDK reachable in this environment, and it would force a Windows-only development loop with a heavier native deployment. **Electron** was rejected: the runtime download is blocked in this environment, it ships a 150+ MB Chromium runtime, its printing path is Chromium-based (weaker Windows printer control) and it complicates LGPL/institutional audits. **Tauri/WinUI**: WebView2 dependency + Rust toolchain unavailable + no browser binary in sandbox. **Qt QML** was rejected in favour of QtWidgets: data-dense tables, print fidelity and deterministic offscreen rendering are all stronger in QtWidgets, and QML's animation advantage is not worth the printing/table cost. |
| UI architecture | **Widget framework + central design-token stylesheet + custom-painted components** | Gives pixel-level control of a premium clinical design language, deterministic rendering for automated visual regression tests, and no per-screen styling drift (one token source, §5). |
| Database | **SQLite 3 (bundled with Python)** in WAL mode, accessed via `sqlite3` with a hand-written, versioned schema + a thin repository layer | Zero-install embedded RDBMS with ACID transactions, `VACUUM INTO` for consistent hot backups, `PRAGMA integrity_check` for verification, foreign keys enforced by default. Alternative **PostgreSQL/MySQL**: requires a service, forbidden by the offline/zero-install constraint. An **ORM** (SQLAlchemy) was considered and rejected: the money/audit/transaction semantics of this product want explicit SQL, explicit `BEGIN IMMEDIATE`, and no lazy-loading surprises; the repository layer keeps SQL in one place and testable. |
| Money | Python **`Decimal`** in the domain, persisted as **INTEGER minor units (paisa)** | Exact decimal-safe accounting, never binary floats; SQLite integer arithmetic is exact and index-friendly. |
| PDF/print | Qt `QTextDocument` (rich text) → `QPrinter` / `QPdfWriter` | Fully offline, high-resolution (300 dpi), uses the Windows print system, supports "Save as PDF" through the normal Windows flow, and preview/print share one render path so the preview is the output. |
| Fonts | **Inter** (UI/latin) + **Noto Sans Bengali** (Bangla), bundled, OFL-1.1 | Deterministic rendering on any Windows machine, no dependency on installed fonts, correct Bengali shaping (verified). |
| Icons | Curated **Lucide** SVG set (ISC) + in-repo custom dental SVGs | Permissive licence, crisp at every DPI, no icon font licensing risk; the app icon is generated programmatically for mathematically clean geometry. |
| Packaging | **PyInstaller 6.x** (onedir) + **NSIS 3** installer | onedir keeps Qt DLLs as replaceable files (satisfies LGPL relinking expectations), starts faster than onefile, and NSIS is free, scriptable, GPL-with-exception (build-time tool, unlimited redistribution of produced installers), and supports shortcuts, file associations, uninstall and clean upgrade behaviour. |
| CI/CD | **GitHub Actions** (`ubuntu-latest` for fast gates, `windows-latest` for packaging/UI goldens) | Mandated by the requirements; Windows runners are the only realistic way to produce and smoke-test the real `.exe` installer for this project. |
| Password hashing | **Argon2id** (`argon2-cffi`, MIT) m=64 MiB, t=3, p=2, 16-byte salt, 32-byte tag | OWASP-recommended memory-hard KDF, pure-offline, no native toolchain needed (prebuilt win_amd64 wheels verified). |
| Backup encryption (optional) | `cryptography` (Apache-2.0/BSD-3) AES-256-GCM + scrypt for passphrase-protected backups | Backups leave the clinic PC on USB drives; optional protection is a real commercial need. Default backups remain unencrypted for recoverability. |
| QR on documents (optional) | `segno` (BSD-3), pure Python | Offline generation of a verification QR (document code + patient code + date) for printed prescription/invoice authenticity. |
| Tests | **pytest**, **pytest-qt**, plus a custom offscreen snapshot harness | Industry standard, MIT-licensed, works headless in CI, and allows true end-to-end in-process driving of the real UI. |

### 3.2 Explicitly rejected technologies and why

- **Any cloud database / online auth / paid API / paid SDK / analytics** — forbidden by the product
  requirement and unnecessary: every feature is local.
- **Electron / Chromium UI** — blocked in the build environment, large runtime, weaker Windows print
  control, and Chromium's PDF path gives less control over mm-precise thermal layouts.
- **.NET WPF / WinUI 3** — best-in-class Windows integration, but the .NET SDK and NuGet feed are
  unreachable here, which would make independent verification impossible in this environment.
- **SQLAlchemy ORM** — see above; explicit SQL keeps transaction and audit semantics auditable.
- **A separate reporting engine (ReportLab/Jasper)** — Qt's print pipeline already covers preview,
  printers, paper sizes and PDF; adding a second engine would double the print test surface.
- **Microservices / client-server split** — the requirement is a single-machine offline product;
  a network layer would add failure modes with no benefit.
- **WebView-based UI inside Qt** — no browser engine is available offline in the target runtime.

---

## 4. Layered architecture

```
                        ┌──────────────────────────────────────────────┐
  Presentation          │  ui/shell      main window, header, sidebar, │
  (PySide6 widgets)     │                router, shortcuts, lock layer │
                        │  ui/screens    dashboard, patients, appts,   │
                        │                queue, clinical, billing,     │
                        │                inventory, accounting, admin  │
                        │  ui/components design-system widgets         │
                        │  ui/wizards    activation, first-run setup   │
                        └───────────────┬──────────────────────────────┘
                                        │  calls only services; never SQL
                        ┌───────────────▼──────────────────────────────┐
  Application services  │  services/*   patients, appointments, queue, │
  (business rules,      │               visits, dental, treatments,    │
   RBAC enforcement,    │               prescriptions, invoicing,       │
   transactions, audit) │               payments, inventory, accounting,│
                        │               reports, search, notifications,│
                        │               users/roles, settings, backup, │
                        │               restore, maintenance, files    │
                        └───────────────┬──────────────────────────────┘
                                        │  repositories + unit of work
                        ┌───────────────▼──────────────────────────────┐
  Data access           │  data/db      connection, PRAGMAs, tx mgr,   │
                        │               migrations, integrity checks   │
                        │  data/repos   one module per aggregate       │
                        │  data/queries read models for lists/reports  │
                        └───────────────┬──────────────────────────────┘
                                        │
                        ┌───────────────▼──────────────────────────────┐
  Persistence           │  SQLite (WAL) + file store (attachments)      │
                        │  backup containers (.dprobackup)              │
                        └──────────────────────────────────────────────┘
  Cross-cutting: core/ (config, paths, logging, errors, money, ids,
  time, workers) · security/ (auth, rbac, audit, activation)
  printing/ (profiles, renderers) · backup/ (writer, verifier, restore)
```

**Hard rules**

1. UI never executes SQL and never reads the database file directly.
2. Every mutating operation goes through a service method that (a) checks permission, (b) opens a
   transaction, (c) writes audit records, (d) returns a domain result.
3. Services never reach into widgets; progress/cancellation is passed in as a callback interface.
4. Long-running work runs in worker threads (`QThread` + worker objects) and communicates via signals;
   the UI thread never blocks on I/O.
5. Only `data/` knows SQL; only `services/` knows business rules; only `ui/` knows pixels.

---

## 5. Runtime topology

- **Process model:** one GUI process (+ short-lived helper processes only for opening external files
  through the OS). No background service, no scheduled task, no network listener.
- **Data root (configurable, chosen in the first-run wizard, changeable in Settings):**
  default `%PROGRAMDATA%\DentivaPro\data` (created by the installer with a *Users:Modify* ACL) with an
  automatic fallback to `%LOCALAPPDATA%\DentivaPro\data` when ProgramData is not writable.
  ```
  <data root>/ dentivapro.db         main database (WAL: -wal, -shm)
               attachments/<patient-id>/<uuid>.<ext>   patient files
               backups/            default backup folder (user-selectable elsewhere)
               exports/            generated CSV/PDF exports
               logs/               structured JSONL logs (rotated)
               activation.dat      protected activation state
               .locks/             single-instance + maintenance locks
  ```
- **Single instance:** an exclusive lock file + `QLocalServer` handshake; a second launch focuses the
  existing window instead of opening a second writer to the same SQLite file.
- **Threading model:** UI thread + worker pool for backup/restore/export/import/attachment hashing;
  SQLite connection per thread with `check_same_thread` enforced; writes serialized through a
  `BEGIN IMMEDIATE` transaction manager with busy-timeout and retry-with-backoff.
- **Locking:** the app lock overlay (auto-lock) is a full-window modal layer; sensitive widgets are
  disabled and their content is masked while locked.
- **Startup sequence:** single-instance guard → data root resolution → log init → DB open + integrity
  quick-check + schema compatibility check → activation check → session restore (if any) or first-run
  wizard/login → main shell.

---

## 6. Configuration model

Three tiers, all explicit:

1. **Build-time constants** (`src/dentivapro/version.py`, platform defaults) — immutable per release.
2. **Machine config** (`%PROGRAMDATA%\DentivaPro\machine.json`) — data root path, installation id,
   activation state pointer, update-free. Written by the installer and the app on first run.
3. **Business settings** (SQLite `settings` table, keyed) — clinic identity, print profiles, auto-lock
   minutes, appointment rules, backup schedule, numbering formats, notification thresholds, defaults.
   Each key is declared in a typed registry (`core/settings_schema.py`) with type, default, validator,
   permission required to change, and whether the change must be audited. Unknown keys are rejected;
   invalid values never reach the database. Settings changes are audited with before/after values.

---

## 7. Error handling, logging and diagnostics

- **Domain errors** (`ValidationError`, `PermissionDenied`, `ConflictError`, `BusinessRuleError`,
  `IntegrityError`, `ActivationError`, `BackupError`, …) carry a user-safe message key plus structured
  context; the UI shows the localized message, never a stack trace.
- **Unexpected exceptions** are caught at the screen level, at the app level (a global `sys.excepthook`
  and Qt message handler) and logged with a correlation id; the user sees an error dialog containing
  the correlation id and a "Copy diagnostic details" action that copies a redacted report.
- **Structured logging** (`core/logging.py`): JSON lines to `logs/dentivapro-YYYYMMDD.jsonl` with
  rotation and retention; fields: timestamp (UTC), level, logger, event, user, session, entity,
  duration, correlation id. Redaction filters strip passwords, activation attempt values, tokens and
  medical free-text from log payloads. Log path and log level are configurable in Settings.
- **No silent failures:** every `except` either re-raises, converts to a domain error, or records a
  logged diagnostic event; a CI check (`tools/check_no_silent_except.py`) fails the build on bare
  `except: pass` patterns in production code.
- **Diagnostics pack** (Settings → About → "Export diagnostics"): a ZIP with app version, machine
  config summary, recent logs, DB `integrity_check` result, table counts, and dependency/licence
  listing — never patient clinical content.

---

## 8. Localization, Bengali and currency

- **Primary application language:** professional English. All user-facing strings come from a single
  message catalogue (`core/i18n.py`) with stable keys — no string literals scattered in widgets — so the
  product is ready for a full Bengali UI later without a refactor.
- **Bengali content support everywhere** a user types: patient names/addresses/notes, clinical findings,
  prescriptions, invoice descriptions, expense notes, clinic identity and letterhead. All text widgets
  use a font fallback chain `Inter → Noto Sans Bengali → system` so mixed Bangla/Latin text shapes
  correctly (verified in this environment, including conjuncts and the ৳ sign).
- **Currency:** BDT only. `core/money.py` provides `Money` (Decimal, 2 dp, banker-free half-up rule
  applied explicitly) with `format(locale='bn-BD')` producing e.g. `৳ 12,450.75`, plus Bengali numeral
  output where used in print templates. Accounting values are persisted as integer paisa.
- **Dates/times:** instants stored as UTC ISO-8601; business dates (visit date, invoice date, payment
  date, expense date) stored as clinic-local `YYYY-MM-DD` so period reports and reprints never shift
  across timezones or DST-like changes. Display follows the Windows locale/format settings.

---

## 9. Performance strategy

Targets (validated against a synthetic clinic of 50 000 patients / ~300 000 clinical + financial rows):
list and search operations p95 ≤ 300 ms; dashboard load ≤ 1.5 s; screen switch ≤ 150 ms; print preview
render ≤ 1 s for a 2-page prescription; backup of 2 GB data ≤ 90 s with progress; no UI freeze > 100 ms.

Techniques: keyset pagination (never `OFFSET` over large sets in the hot path), covering indexes for the
search columns, projection-limited queries for lists, cached aggregate tables for dashboard counters
invalidated by the writing service, virtualized Qt table views with custom models, deferred loading of
patient-profile tabs, batched attachment hashing, and `PRAGMA` tuning (`journal_mode=WAL`,
`synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout`, `temp_store=MEMORY`, `mmap_size`).

---

## 10. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| No Windows machine in this environment | Can't run the EXE here | Windows-only validation executed on GitHub Actions `windows-latest` (offscreen UI goldens + packaged-bundle smoke test + installer build); documented as a limitation with the exact CI evidence to attach |
| GitHub Actions may not run / logs unreadable with this token | No CI-produced installer evidence | Phase 1 immediately pushes a minimal CI workflow and verifies whether runs execute and whether status is visible; if not, the fallback path is documented in the Phase report and `dist/` |
| Qt LGPL compliance for a commercial closed-source app | Legal exposure | Dynamic linking via onedir (DLLs remain replaceable files), full licence texts shipped in `assets/notices/` and in the installer, no Qt modifications, Qt version pinned; audit re-run in Phase 10 |
| Thermal/Bluetooth printer quirks | Broken receipts | Dedicated 58/80 mm templates (not scaled A4), paper-capability detection with graceful, explicit failure messages, and per-profile testing matrix |
| Bengali shaping differences across Windows versions | Broken Bangla text | Fonts are bundled and registered explicitly; golden-image tests assert shaping |
| Single-PC data loss | Clinic data loss | Mandatory backup subsystem with verified containers, pre-restore safety backups, integrity checks, and scheduled reminders |
| Scope size | Phase drift | Strict phase gates, per-phase reports, traceability matrix updated every phase |

---

## 11. Related documents

- `01-domain-and-data-model.md` — entities, keys, indexes, integrity, deletion rules
- `02-security-and-rbac.md` — authentication, RBAC matrix, audit, activation design
- `03-ui-and-design-system.md` — design tokens, components, shell, DPI/responsive behaviour
- `04-printing-and-documents.md` — print engine, profiles, failure handling, determinism
- `05-backup-and-restore.md` — container format, verification, atomic restore, scheduling
- `06-testing-and-quality.md` — test levels, tooling, performance/security testing, quality gates
- `07-build-installer-ci-release.md` — packaging, installer, CI/CD, versioning, release strategy
- `08-dependency-license-audit.md` — dependency inventory, licences, redistribution obligations
- `../requirements-traceability.md` — requirement → design → code → test mapping
- `../acceptance-test-matrix.md` — formal acceptance tests per phase
- `../environment-and-limitations.md` — what this environment can and cannot verify
