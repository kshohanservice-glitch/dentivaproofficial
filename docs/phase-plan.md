# Dentiva Pro — Phase Execution Plan (18 phases)

This plan is the execution protocol of the master specification, phase for phase. Work is strictly
sequential: a phase closes only when its acceptance gate passes, a phase report is written into
`docs/phase-reports/`, and the agent **stops and waits for the user to say "Continue"**. Nothing is
carried into a later phase silently, and no two phases are merged.

> **Numbering note.** An earlier draft of this plan used a compressed 13-phase numbering (0–12). It has
> been replaced by the specification's own 18 phases so that every report, screen label and traceability
> row refers to the same phase numbers the owner uses. The work already completed was re-mapped, not
> re-done and not lost: discovery/architecture = Phase 1, engineering foundation and design system =
> Phase 2. `docs/requirements-traceability.md` carries the full mapping.

---

## Status at a glance

| Phase | Name | Status |
|---|---|---|
| 1 | Product Discovery, Requirements Freeze and Technical Planning | **Complete** (report: `phase-01-report.md`) |
| 2 | Repository, Engineering Foundation and Design System | **Complete pending the PR gate** (report: `phase-02-report.md`) |
| 3 | Database, Domain Model, Security and RBAC | Not started |
| 4 | Premium Application Shell and Core UI | Not started |
| 5 | Clinic Setup, Dentists, Staff, Users and Administration | Not started |
| 6 | Patients, Profiles and Attachments | Not started |
| 7 | Visits, Clinical Timeline, Dental Chart and Treatments | Not started |
| 8 | Appointments and Queue | Not started |
| 9 | Prescriptions and Clinical Document Engine | Not started |
| 10 | Invoice, Payments and Financial Controls | Not started |
| 11 | Inventory and Accounting | Not started |
| 12 | Search, Notifications, Dashboard and Operational Intelligence | Not started |
| 13 | Backup, Restore, Import/Export and Data Integrity | Not started |
| 14 | Printing, PDF and Printer Profiles Finalization | Not started |
| 15 | Security, Audit, Performance and UX Hardening | Not started |
| 16 | Full QA, Stress Testing and Regression | Not started |
| 17 | Installer and Release Candidate | Not started |
| 18 | Final Audit, GitHub Actions and Production Release | Not started |

---

## Phase 1 — Product Discovery, Requirements Freeze and Technical Planning

**Deliverables:** repository and environment inspection; requirement baseline extracted from the master
specification; technology decisions with written justification and rejected alternatives; architecture,
domain/data-model, security/RBAC, UI/design-system, printing/document, backup/restore, testing, CI/build
and release plans; dependency and licence audit; requirements traceability matrix (120 requirement
groups); acceptance test matrix (AT-001…AT-171); phase plan (this document); environment limitations.

**Acceptance gate:** the plan is complete, internally consistent, and every capability it depends on has
been proven by an executed probe (Qt rendering, Bengali shaping, offline PDF, SQLite capability and
performance, Argon2id cost, Windows wheel availability, packaging toolchain, GitHub capability).
No application feature is built in this phase.

**Evidence:** `docs/architecture/00…08`, `docs/requirements-traceability.md`,
`docs/acceptance-test-matrix.md`, `docs/environment-and-limitations.md`, `docs/phase-reports/phase-01-report.md`.

---

## Phase 2 — Repository, Engineering Foundation and Design System

**Deliverables:** project structure (src layout, pinned dependencies); Python 3.12 environment and
dependency management; ruff/mypy/pytest/coverage configuration; database connection, migration discovery
and schema-history foundation; structured logging with redaction; configuration and data-root resolution;
secure secret handling (secret scanner, no plaintext secrets); the UI design system (tokens, theme,
bundled Inter + Noto Sans Bengali, icon set, components); the application shell foundation (header,
collapsible sidebar, navigation model, router, shortcuts, error boundary, toasts, status bar); the
app icon set and Windows icon resource; the initial documentation set; GitHub Actions baseline
(quality gates, Linux tests, Windows bundle/installer/smoke test); foundational test suite; Windows
packaging pipeline (PyInstaller spec, NSIS installer, bundle audit, version resource).

**Acceptance gate:** every quality gate green on the development sandbox **and** in CI; the shell renders
correctly at every supported window size and display scale with committed golden fingerprints; the
application starts, initialises its database and reports a clean integrity check; the Windows job builds
the `.exe`, builds the installer, silently installs, launches, verifies database initialisation and
uninstalls; a pull request is open for review and **not merged by the agent**.

**Evidence:** `docs/phase-reports/phase-02-report.md`, the committed test suite, the CI run of the phase
commit, and the Windows artefacts attached to that run.

---

## Phase 3 — Database, Domain Model, Security and RBAC

**Deliverables:** the complete relational schema (clinic, users/roles/permissions, staff/dentists,
patients, attachments, visits, clinical findings, dental chart, tooth findings, treatment catalogue,
prescriptions and items, appointments, queue, invoices and items, payments, inventory, suppliers,
purchases, stock movements, expenses, income, referrals, notifications, audit log, backups, printer
profiles, settings); migrations for every step; repository/data-access layer; domain and business services;
authentication with Argon2id (unique salts), password policy, throttling and lockout; session management
and auto-lock (5/10/15/30 minutes); granular RBAC with permission enforcement in the service/query layer;
audit foundation (append-only, tamper-resistant); financial permission enforcement; activation verification
(derived, non-plaintext, offline).

**Acceptance gate:** schema/FK/migration/integrity tests green; permission matrix tests green, including
direct service and query access attempts with no UI involvement; password/lockout/session/lock/unlock tests
green; audit coverage and immutability tests green; activation tests green with the code absent as
plaintext; secret scan green.

---

## Phase 4 — Premium Application Shell and Core UI

**Deliverables:** finalised application shell (global header with identity, clinic, date, notification
centre and user/session area; collapsible sidebar preserving state; every route reachable); the complete
component library (buttons, fields, selects, date/time pickers, tables, tabs, cards, dialogs, drawers,
menus, tooltips, badges, status indicators, banners, pagination); the state system (loading, empty, error,
success, disabled, no-permission, validation) wired into every screen contract; dialog and drawer
framework; notification/toast framework; global search framework; keyboard shortcut framework with a
shortcut reference dialog; High-DPI and resize behaviour audited at 1366×768, 1920×1080, 2560×1440 and
3840×2160 at 100 %, 125 %, 150 %, 175 % and 200 % scaling; subscription to the responsive grid rules
(no accidental card wrapping); motion/animation standards; visual QA pass with golden fingerprints
re-promoted.

**Acceptance gate:** every interactive element in the shell works and is tested; layout invariants proven
at every supported size/scale (no clipping, no overlap, no horizontal overflow, no unreachable content);
all state contracts render; goldens re-promoted deliberately; UI defect checklist executed with fixes.

---

## Phase 5 — Clinic Setup, Dentists, Staff, Users and Administration

**Deliverables:** transactional, resumable first-run setup wizard (clinic identity and logo, contact
details, one or many dentists with structured designations and certifications/qualifications, initial
administrator account, currency, document and printing defaults, security/session defaults, backup
defaults) that blocks normal production use until complete; clinic/dentist/signature administration;
staff registry (photo, identification, contact, salary, joining, status) separated from login accounts;
user management; role and permission management with the granular catalogue; the Settings module
(safe vs destructive changes distinguished); About screen; audit coverage for every administrative action.

**Acceptance gate:** setup happy path, interruption and atomicity tests green; no partially initialised
database is possible; staff/user/role/permission acceptance tests green; permission changes take effect
immediately; settings validation and destructive-guard tests green.

---

## Phase 6 — Patients, Profiles and Attachments

**Deliverables:** patient registration with validation, patient code generation and uniqueness, duplicate
detection that never silently merges; patient list with Today/7/30/90-day/1-year/custom filters, sorting
and paging that stays fast at 50 000+ records; the longitudinal patient profile (overview, personal
information, contact, medical/dental history, activity, financial summary, outstanding balance) with
context-preserving actions; attachments (validated types/sizes, metadata, preview, missing-file
tolerance, permission checks); patient search; patient-related permissions enforced in services.

**Acceptance gate:** realistic patient workflows green; duplicate detection tests green; attachment
security/validation tests green; 50 k-record performance budget green; Bengali patient data round-trips
through every surface; no artificial record cap anywhere.

---

## Phase 7 — Visits, Clinical Timeline, Dental Chart and Treatments

**Deliverables:** the visit system (each visit a separate immutable-by-default historical event with
attending dentist, complaint, examination, findings, diagnosis, treatments performed, advice, follow-up,
notes, links to prescription/invoice/payment/attachments); clinical timeline (registration, visit,
chart update, treatment, prescription, appointment, invoice, payment, referral, attachment) with
navigation into each record; the interactive dental chart (adult FDI 11–48 and primary 51–85, multi-tooth
selection, status per tooth and per visit, historical states preserved); structured clinical findings
catalogues with custom free text; treatment catalogue with categories, default prices, active/inactive;
referral management (referring dentist, destination provider, reason, notes, status, follow-up);
controlled, audited editing of historical clinical records.

**Acceptance gate:** longitudinal history tests green (earlier visits never overwritten); chart history
and tooth-status tests green; treatment catalogue and price-history tests green (historical invoices keep
the charged price); referral tests green; audit coverage for clinical edits green.

---

## Phase 8 — Appointments and Queue

**Deliverables:** appointment scheduling with dentist, date/time, duration, reason and status
(scheduled, confirmed, arrived, completed, missed/no-show, cancelled, rescheduled); appointment history
preserved; conflict handling; creation from the module and from the patient profile (context inherited);
clinic queue with the states waiting, called, in consultation, completed, skipped, cancelled; efficient
queue updates without full-screen reloads; queue visibility on the dashboard later in Phase 12.

**Acceptance gate:** appointment lifecycle and status-transition tests green; double-booking rules green;
queue workflow tests green; permission tests green; UI tests for the appointment and queue screens.

---

## Phase 9 — Prescriptions and Clinical Document Engine

**Deliverables:** prescription editor (patient and dentist selection, multiple medicines with form,
strength, dose, frequency, morning/noon/night schedule, before/after meal, duration, quantity, PRN,
instructions; structured plus free-text clinical sections C/C, O/E, R/E/Advice); medicine catalogue;
configurable clinical terminology; the document rendering architecture (document model → layout engine →
paper profile → preview → printer selection → output); prescription document design (clinic identity and
logo, dentist identity with multiple designations and qualifications, patient block, clinical sections,
medicine table, footer, protected blank signature area); print preview; printer selection; PDF output;
A4/A5/thermal profiles at this stage.

**Acceptance gate:** multi-medicine and long-content pagination tests green; no overlap or clipping at
any profile; Bengali and mixed-language prescription tests green in preview, PDF text extraction and
rendered output; the signature area stays clear of printed content; printing matrix artefacts reviewed.

---

## Phase 10 — Invoice, Payments and Financial Controls

**Deliverables:** treatment billing with catalogue pricing frozen into invoice lines; invoices with
subtotal, discount, total, paid, due and payment status; full, partial, deferred and no-payment flows;
payment ledger with methods (cash, bank, card, bKash, Nagad, Rocket, Upay, other), reference numbers,
received-by and notes; patient financial history (billed, paid, outstanding, payment dates and methods,
adjustments); outstanding balance derived from transactional data only; invoice print and PDF in A4/A5/
thermal/mini formats; financial permissions enforced in services and queries; void/reversal with audit.

**Acceptance gate:** money-exactness tests (integer paisa, no float drift); invoice/payment consistency
tests including partial and later payments; financial permission-denial tests including direct service
calls, search, reports and exports; invoice printing and PDF tests green.

---

## Phase 11 — Inventory and Accounting

**Deliverables:** inventory items (category, supplier, purchase source and date, batch/lot, quantity,
current stock, unit cost, expiry, low-stock threshold, notes); purchases; stock movements and adjustments
through controlled business logic; expiry monitoring and low-stock alerts; inactive items keep their
history; income and expense records with configurable categories (rent, electricity, internet, supplies,
salary, maintenance, other); daily/monthly/yearly/custom-period financial reports; integration with the
payment ledger; audit for every stock and accounting change.

**Acceptance gate:** stock-ledger integrity tests (no drift, no negative stock, no destroyed history);
expiry/low-stock accuracy tests; accounting totals reconciled against payments and expenses; report
accuracy verified against independent calculation; permission tests green.

---

## Phase 12 — Search, Notifications, Dashboard and Operational Intelligence

**Deliverables:** global search across patients, codes, phone numbers, visits, prescriptions,
appointments, invoices, payments, inventory and staff with filters and permission-aware results;
notification centre (upcoming and missed appointments, outstanding payments, low stock, expiring
inventory, backup results, security events, system warnings) with read/unread state and permission
context; operational dashboard with real data (today's patients, appointments, queue, completed visits,
pending appointments, today's revenue, outstanding dues, low stock, expiring inventory, recent patients,
recent payments, upcoming appointments, clinical activity, quick actions) on a deliberate responsive grid;
operational reports.

**Acceptance gate:** search permission-leak tests green; notification correctness and permission tests
green; dashboard numbers verified against underlying transactions; empty/loading/error states for every
widget; performance budgets green with large datasets.

---

## Phase 13 — Backup, Restore, Import/Export and Data Integrity

**Deliverables:** manual backup to a native folder-selection destination with timestamped filenames and
atomic creation (temporary file, verification, rename); backup container (database snapshot, attachments,
manifest with hashes); backup verification; scheduled automatic backups at 7/15/30-day intervals working
without any cloud service; restore with integrity validation, pre-restore safety backup, staged swap and
rollback on failure; recovery from interruption; controlled CSV import/export with preview, validation,
duplicate detection, error report and permission enforcement; retention/archival policy
(archive vs soft delete vs hard delete vs destructive reset) with safeguards.

**Acceptance gate:** backup/restore acceptance suite green including failure paths (interrupted backup,
corrupt backup, disk full, permission denied, locked file); a real backup → restore → verify cycle
executed and evidenced; destructive operations guarded by typed confirmation, re-authentication and
safety backups; import cannot corrupt relational integrity.

---

## Phase 14 — Printing, PDF and Printer Profiles Finalization

**Deliverables:** print-system hardening across the document family (prescription, invoice, receipt,
thermal, reports, clinical summaries); paper profiles finalised (A4, A5, 58 mm, 80 mm, mini/receipt and
custom dimensions); printer selection and profile-to-printer compatibility handling; print preview
fidelity; PDF output with embedded Unicode fonts; Bengali and mixed-script fidelity on every profile;
multi-page pagination for long content; High-DPI sharpness; failure handling for missing printers,
driver errors and paper mismatch.

**Acceptance gate:** the complete print matrix runs green with reviewed artefacts; PDFs are text-extractable
and correct for Latin and Bengali; no profile produces clipping, overlap or lost content; signature areas
remain writable after printing.

---

## Phase 15 — Security, Audit, Performance and UX Hardening

**Deliverables:** full security review (authentication, session, auto-lock, activation, RBAC bypass
attempts, financial permission enforcement, path traversal, upload validation, SQL parameterisation,
secret handling, logging redaction); audit review (coverage, immutability, before/after payloads);
data-integrity review; performance optimisation against documented budgets; memory/resource review;
UI/UX hardening (alignment, spacing, overflow, focus states, keyboard traversal, states); accessibility
and usability review; centralised error handling review.

**Acceptance gate:** zero open critical or high findings; every fix covered by a regression test; budgets
green under load; UI defect checklist re-executed.

---

## Phase 16 — Full QA, Stress Testing and Regression

**Deliverables:** the complete automated suite (unit, integration, service, security, printing, UI,
performance, acceptance) plus stress testing: large patient counts, patients with many visits, long
timelines, many prescriptions, long invoices, many payments, large attachment collections, large search
result sets, inventory history, backup/restore with realistic data sizes, low disk space, repeated
navigation, long sessions, repeated lock/unlock; leak, hang, deadlock and lock detection.

**Acceptance gate:** all suites green; no release-blocking defect open; every defect found during the
phase fixed and retested; the end-to-end clinic workflow (the specification's acceptance walkthrough)
executed step by step with evidence.

---

## Phase 17 — Installer and Release Candidate

**Deliverables:** release candidate built by CI; installer validation on a clean Windows environment
(install, shortcuts, icon, first-run setup, activation, all primary workflows, printing, backup location,
uninstall with explicit data choice, reinstall); release-candidate audit.

**Acceptance gate:** every release-candidate acceptance item passes with evidence; any failure blocks the
release and forces a fix plus a full re-run of the affected checks.

---

## Phase 18 — Final Audit, GitHub Actions and Production Release

**Deliverables:** requirement-by-requirement final audit against the traceability matrix (implemented,
verified, tested, passed); dead-code, TODO and placeholder review; dependency and licence audit
confirmation; final CI run; production `.exe` build, integrity verification and GitHub Release publication
(or, if publication is impossible, the verified artefact placed in the repository `dist/` directory with
an honest explanation); final release report.

**Acceptance gate:** every requirement marked implemented, verified, tested and passed; CI green; the
artefact verified; the final report published. No pull request is ever merged by the agent.

---

## Rules carried through every phase

- Never merge a pull request; the repository owner decides. Stop at the PR gate.
- Never silently downgrade a requirement: document the limitation, implement the best valid alternative,
  and report it.
- Fix defects found in earlier phases immediately, with a regression test.
- Keep the traceability matrix updated in the same change as the work.
- Re-verify (never assume) the repository state when resuming after an interruption.
- Every phase ends with a report in `docs/phase-reports/` and a stop for the owner's "Continue".
