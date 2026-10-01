# Dentiva Pro — Requirements Traceability Matrix

Every requirement group from the master specification is listed here with its design reference,
implementing module, verification method, phase, and status. `tools/qa/check_traceability.py` verifies in
CI that each row has a real test id present in the suite and that no row is left `not started` at release.

**Status legend:** `planned` → `in progress` → `done` (implemented **and** verified) · `blocked` (with a
documented reason, never silent).

| ID | Requirement (condensed) | Design ref | Implementation | Verification | Phase | Status |
|---|---|---|---|---|---|---|
| R-01 | Product is a real commercial offline Windows desktop app, no demo/mock/placeholder content | 00 | whole repo | `qa/check_no_placeholders`, packaging test (no sample data in bundle) | 1–12 | planned |
| R-02 | No internet required after installation/activation; no paid API/SDK/cloud/subscription | 00 §3, 08 §3 | whole repo | offline launch test, dependency audit, `qa/check_offline.py` | all | planned |
| R-03 | Bangladesh-specific: English UI, Bengali Unicode input everywhere, BDT with ৳ | 00 §8 | `core/i18n`, `core/money`, `ui/design/text` | `tests/unit/test_money.py`, `tests/ui/test_bengali.py`, printing Bengali matrix | 1, 4–6 | planned |
| R-04 | Exact decimal money handling (no binary floats for accounting) | 01 §1 | `core/money`, all money columns as integer paisa | `tests/unit/test_money.py`, `tests/integration/test_money_persistence.py`, Grep gate for float in finance | 2, 6 | planned |
| R-05 | Premium flagship clinical design language, consistent design tokens, no per-screen styling | 03 | `ui/design/*`, `ui/components/*` | token-lint gate, UI goldens, UI review checklist | 1 and every UI phase | planned |
| R-06 | App shell: header (identity, clinic, date, notifications, user) + collapsible sidebar with Practice/Clinical/Billing/Administration and the named modules | 03 §3 | `ui/shell/*`, `ui/screens/*` | `tests/ui/test_shell.py`, route checklist test | 1 | planned |
| R-07 | First-run setup wizard: clinic info, logo, address, phone, dentists (multiple, with designations, certifications, qualifications, signature config), admin account, currency, printing, config | 01 §5.2, 03 | `ui/wizards/setup/*`, `services/setup_service.py` | `tests/acceptance/test_first_run_setup.py` | 3 | planned |
| R-08 | Setup is transactional and recoverable; no half-initialised data | 01 §5.2 | setup in a single transaction + resumable wizard state | `tests/integration/test_setup_atomicity.py`, interruption test | 3 | planned |
| R-09 | Post-setup configurability of clinic/dentists/settings | 03, 01 | Settings screens | `tests/acceptance/test_settings_admin.py` | 3, 8 | planned |
| R-10 | Secure authentication; no plaintext passwords; Argon2id; validation; throttling; sessions; lockout; invalidation | 02 §2–3 | `security/auth.py`, `security/session.py` | `tests/security/test_auth.py`, `test_lockout.py` | 2 | planned |
| R-11 | Auto-lock at 5/10/15/30 min with a lock screen that blocks sensitive interaction | 02 §3, 03 | `services/session_service.py`, `ui/shell/lock_layer.py` | `tests/acceptance/test_autolock.py` | 2 | planned |
| R-12 | Granular RBAC; admin can create users/roles/permissions; staff without financial access | 02 §4 | `security/rbac.py`, `ui/screens/admin/*` | `tests/security/test_permission_matrix.py` | 2, 3 | planned |
| R-13 | Permissions enforced in business/service layer (and query guards), not only UI | 02 §4.1, §4.4 | services + `data/repos/_guard.py` | `tests/security/test_no_ui_only_authz.py`, statement spy | 2 | planned |
| R-14 | Audit trail for security/business-critical actions with user/action/time/entity/before-after; not casually editable | 02 §5 | `security/audit.py`, `audit_log` + triggers | `tests/acceptance/test_audit_coverage.py`, immutability test | 2 | planned |
| R-15 | Patient management: unlimited practical records, no artificial cap | 01 §2.3 | `services/patient_service.py` | perf test with 50 k+ patients, no LIMIT caps in code | 4, 9 | planned |
| R-16 | Patient list date views (today/7/30/90/1y/custom), newest first | 01 §4, 03 | patient list filters | `tests/acceptance/test_patient_filters.py` | 4 | planned |
| R-17 | Fast patient search across multiple fields | 01 §2.3, §4 | `search_blob` + indexes | `tests/perf/test_patient_search.py` | 4, 9 | planned |
| R-18 | Patient registration fields incl. demographics, contacts, chief complaint, history, notes; required-field validation | 01 §2.3 | patient form + validators | `tests/services/test_patient_validation.py` | 4 | planned |
| R-19 | Longitudinal patient profile as a workspace (identity, contacts, medical history, activity, visits, treatments, prescriptions, appointments, billing, payments, outstanding, attachments, notes) | 01 §2.3 | `ui/screens/patients/profile/*` | `tests/acceptance/test_patient_profile.py` | 4 | planned |
| R-20 | Every visit is a separate historical event; previous visits never overwritten | 01 §2.3 | `visit` rows | `tests/acceptance/test_repeated_visits.py` | 4 | planned |
| R-21 | Create visit/appointment/invoice/prescription/payment/attachment from the patient profile without losing context | 03 | profile action bar + drawers | `tests/acceptance/test_patient_context_actions.py` | 4–6 | planned |
| R-22 | New Visit workflow fields (reason, C/C, findings, examination, diagnosis, treatment performed/notes, teeth, prescribed medicines, recommendations, follow-up, referral) | 01, 03 | `ui/screens/clinical/visit_editor.py` | `tests/acceptance/test_visit_workflow.py` | 4, 5 | planned |
| R-23 | Complete clinical timeline (registration, appointments, visits, treatments, prescriptions, invoices, payments, referrals, attachments) | 03 | `ui/components/timeline_view.py` | `tests/acceptance/test_timeline.py` | 4 | planned |
| R-24 | Professional dental chart, adult + pediatric numbering, single/multi selection, persisted structurally | 01 §2.3, 03 | `ui/components/odontogram.py`, `tooth_record` | `tests/services/test_dental_chart.py`, UI golden, persistence test | 4 | planned |
| R-25 | Treatment catalog: names, categories, codes, default prices, active/inactive, usable in visits and billing | 01 §2.3 | `services/treatment_service.py` | `tests/acceptance/test_treatment_catalog.py` | 4 | planned |
| R-26 | Prescription module from profile and main section; multiple medicines with full dosage metadata; add/edit/reorder/remove safely | 01 §2.3 | `ui/screens/clinical/prescription_editor.py` | `tests/acceptance/test_prescription_multiple_medicines.py` | 5 | planned |
| R-27 | Structured selectable C/C and O/E findings (requested defaults) + free text; configurable, not hardcoded | 01 §2.3 | `finding_catalog` seeds + picker | `tests/acceptance/test_finding_catalog.py` | 5 | planned |
| R-28 | C/C, O/E, R/E/Advice sections combining structured and free-form text | 01, 04 | template + editor | `tests/printing/test_prescription_sections.py` | 5 | planned |
| R-29 | Premium prescription print design with clinic + dentist identity, multiple designations/qualifications | 04 §4.1 | `printing/templates/prescription.html` | printing matrix + artifact review | 5 | planned |
| R-30 | Prescription signature area with large reserved blank space that cannot collapse | 04 §4.1, §5 | fixed-height footer block | `tests/printing/test_signature_area.py` (min 22 mm at all content sizes) | 5 | planned |
| R-31 | Print/export through the Windows print system: A4/A5/thermal/wireless/Bluetooth, Save as PDF | 04 | `printing/print_service.py` | printing matrix, windows CI smoke | 5, 11 | planned |
| R-32 | Print preview, printer/paper selection, graceful failure explanation | 04 §6 | `ui/components/print_preview.py` | `tests/printing/test_printer_failures.py` | 5 | planned |
| R-33 | Invoice premium design: clinic-only header; items, qty, unit price, line totals, subtotal, discounts, adjustments, total, paid, due, status | 04 §4.2 | invoice template + editor | `tests/acceptance/test_invoice_flow.py` | 6 | planned |
| R-34 | Payments separate and auditable; multiple payments per invoice; never overwrite totals | 01 §2.5 | `services/payment_service.py`, `payment` rows | `tests/acceptance/test_multiple_payments.py` | 6 | planned |
| R-35 | Payment methods incl. cash/bank/card/bKash/Nagad/Rocket/Upay/other with reference info | 01 §2.5 | payment form + enum | `tests/services/test_payment_methods.py` | 6 | planned |
| R-36 | Payment date reporting (today/7/30/90/1y/custom) with daily totals and method summary | 01 §8 | `data/queries/payment_day_view` | `tests/acceptance/test_payment_reports.py` | 6 | planned |
| R-37 | Financial permissions enforced at business level incl. reports and payment details | 02 §4 | finance services + guards | permission matrix tests | 6 | planned |
| R-38 | Inventory: items, categories, SKU, supplier, purchase info, units, stock, min threshold, cost, expiry, batch, notes | 01 §2.6 | `services/inventory_service.py` | `tests/acceptance/test_inventory.py` | 6 | planned |
| R-39 | Stock movements only (no inconsistent manual stock edits); traceable ledger | 01 §2.6 | `inventory_movement` + cache recompute | `tests/services/test_stock_ledger.py` | 6 | planned |
| R-40 | Expiry tracking and low-stock alerts | 01, 03 | alert queries + notification sources | `tests/acceptance/test_inventory_alerts.py` | 6 | planned |
| R-41 | Accounting income/expenses with categories, auditable records | 01 §2.5 | `services/expense_service.py` | `tests/acceptance/test_accounting.py` | 6 | planned |
| R-42 | Financial reports: daily/weekly/monthly/quarterly/yearly/custom; income, expenses, collections, receivables | 01 §8 | `data/queries/finance_period_view` | `tests/acceptance/test_finance_reports.py` | 6 | planned |
| R-43 | Dashboard: genuinely operational widgets, permission-aware (no financial leaks) | 03, 02 | `ui/screens/practice/dashboard.py` | `tests/acceptance/test_dashboard_permissions.py` | 7 | planned |
| R-44 | Appointments: calendar/list, statuses, creation with patient/dentist/date/time/duration/reason/notes, conflict handling, traceability | 01 §2.4 | `services/appointment_service.py` | `tests/acceptance/test_appointments.py`, conflict tests | 5 | planned |
| R-45 | Queue: waiting/in consultation/completed/cancelled, dentist-specific, synchronised with visits | 01 §2.4 | `services/queue_service.py` | `tests/acceptance/test_queue.py` | 5 | planned |
| R-46 | Referral management (reason, destination, date, notes, follow-up) in patient history | 01 §2.3 | `services/referral_service.py` | `tests/acceptance/test_referrals.py` | 4 | planned |
| R-47 | Patient attachments: add/view/remove safely; included in backup | 01 §7, 05 | `services/attachment_service.py` | `tests/security/test_attachment_safety.py`, backup tests | 4, 8 | planned |
| R-48 | Advanced global search across entities, permission-filtered, no leaks | 03, 02 | `services/search_service.py` | `tests/acceptance/test_global_search.py` | 7 | planned |
| R-49 | Keyboard shortcuts for common workflows, non-interfering | 03 §6 | `ui/shell/shortcuts.py` | `tests/ui/test_shortcuts.py` | 1, 7 | planned |
| R-50 | Centralised notification centre: appointments, inventory, expiry, backup, security; permission-aware; not noisy | 03 §3 | `services/notification_service.py` | `tests/acceptance/test_notifications.py` | 7 | planned |
| R-51 | Comprehensive Settings (clinic, dentists, prescription/invoice, printing, paper, hours, appointment/queue, catalogues, medicine defaults, payments, inventory, notifications, backup, security, auto-lock, users/roles, data, localization) | 03, 01 | `ui/screens/admin/settings/*` | `tests/acceptance/test_settings_admin.py` | 3, 8 | planned |
| R-52 | Destructive actions protected: permissions, explicit confirmation, typed phrases, consequence explanation | 05 §7 | destructive-action guards | `tests/security/test_destructive_guards.py` | 8 | planned |
| R-53 | About section with Dentiva Pro identity and creator (Shohan Khan, helloiamshohan@gmail.com); no internal tech leakage | 03 | `ui/screens/admin/about.py` | `tests/ui/test_about.py` | 7, 8 | planned |
| R-54 | Backup: local folder via native dialog, deterministic date-time naming, includes all data + attachments | 05 §1–3 | `backup/writer.py` | `tests/backup/test_backup_create.py` | 8 | planned |
| R-55 | Automatic backups at 7/15/30-day intervals, understandable and reliable | 05 §5 | `backup/scheduler.py` | `tests/backup/test_schedule.py` | 8 | planned |
| R-56 | Restore: select one/multiple, pre-restore safety backup, integrity validation, no change on validation failure | 05 §4 | `backup/restore.py` | `tests/backup/test_restore.py` | 8 | planned |
| R-57 | Backup/restore transactional and failure-safe; honest status reporting | 05 §3–4 | staging + atomic swap + run records | `tests/backup/test_failure_paths.py` | 8 | planned |
| R-58 | One-time offline activation with fixed code, never stored in plaintext, derived verification, protected state, honest limitation | 02 §7 | `security/activation.py`, `tools/derive_activation_constants.py` | `tests/security/test_activation.py`, `qa/check_secrets.py` | 2 | planned |
| R-59 | Activation robust to corruption, survives restart, useful error messages without crypto detail | 02 §7 | activation state | `tests/security/test_activation_state.py` | 2, 11 | planned |
| R-60 | Windows install/uninstall: files, shortcuts, registration, data preservation policy, clean removal | 07 §4 | `packaging/installer.nsi` | installer smoke test in CI, clean-machine checklist | 1, 11 | planned |
| R-61 | Installer tested on a clean environment: install → launch → activate → setup → restart → backup → restore → print → PDF → uninstall → reinstall | 07 §3, 06 §6 | CI installer smoke + manual checklist | Phase 11 acceptance record | 11 | planned |
| R-62 | High-DPI support (100–200 %) without blur/clipping/microscopic text | 03 §2.6 | tokens + Qt DPI policy | golden tests at 5 DPI levels | 1, 9 | planned |
| R-63 | Adapt to practical Windows screen sizes/aspect ratios (desktop responsive) | 03 §2.6 | responsive layout rules | layout invariant tests at 4 sizes | 9 | planned |
| R-64 | Every screen has intentional empty/loading/success/warning/validation/permission-denied/data-error states | 03 §5 | components + screens | route state checklist test, UI goldens | all | planned |
| R-65 | No fake buttons: every control works or does not exist | 03 §9 | whole UI | interaction tests + manual UI review checklist | all | planned |
| R-66 | No TODO/placeholder/mock/dead code/coming-soon in the final build | 06 §4 | whole repo | `qa/check_no_placeholders`, `check_dead_code` | 10, 12 | planned |
| R-67 | Database design with keys, FKs, indexes, constraints, timestamps, audit metadata, transactions, deletion rules | 01 | `data/schema/*.sql` | schema tests, FK check, index review | 2 | planned |
| R-68 | No destructive hard deletion for traceable entities; soft delete/void/adjustment instead | 01 §5.4 | services + schema | `tests/services/test_retention_rules.py` | 2–6 | planned |
| R-69 | Historical records stable when staff/dentists/treatments/config change (snapshots) | 01 §1, §5 | snapshot columns | `tests/services/test_snapshots.py` | 4–6 | planned |
| R-70 | Financial records immutable after posting; corrections via adjustment/void/reversal | 01 §2.5, §5.4 | finance services | `tests/services/test_financial_immutability.py` | 6 | planned |
| R-71 | Business identifiers unique and collision-safe | 01 §3 | `sequence` allocation | `tests/integration/test_code_allocation.py` (incl. threaded) | 2 | planned |
| R-72 | Consistent date/time handling; UTC instants + local business dates; no drift | 00 §8, 01 §1 | `core/time` | `tests/unit/test_time.py` | 2 | planned |
| R-73 | Bengali Unicode tested in data and printed/PDF output without corruption/clipping | 03 §2.2, 04 | fonts + templates | Bengali matrix incl. PDF glyph checks | 4–6, 9 | planned |
| R-74 | Printing as a first-class subsystem: profiles, mm-accurate layout, page breaks, no orphaned sections | 04 | `printing/*` | printing matrix | 5 | planned |
| R-75 | Preview matches final output as closely as technically possible | 04 §5 | single render path | golden comparison preview vs PDF | 5 | planned |
| R-76 | Deterministic rendering for the same record + profile | 04 §7 | snapshots + template version | determinism test (byte comparison) | 5 | planned |
| R-77 | Local/offline PDF generation (no paid service) | 04 §1 | QPdfWriter | offline PDF test | 5 | planned |
| R-78 | Clear relationship between clinical and financial data without mixing workflows | 03 | navigation/structure | UI review checklist | 4–7 | planned |
| R-79 | Validation at UI, business and database layers | 01 §1, 06 | validators + CHECK constraints | `tests/services/test_validation_layers.py` | 2–6 | planned |
| R-80 | Deliberate error handling; no swallowed errors; user-safe messages; technical detail logged | 00 §7 | `core/errors`, UI error boundary | `qa/check_no_silent_except`, error-path tests | 1, 10 | planned |
| R-81 | Structured logging, privacy-respecting, no secrets/medical content in logs | 00 §7 | `core/logging` | `tests/unit/test_log_redaction.py` | 1, 10 | planned |
| R-82 | Diagnostics mechanism without exposing developer tooling | 00 §7 | diagnostics export | `tests/ui/test_diagnostics.py` | 7, 10 | planned |
| R-83 | Performance with large realistic datasets (pagination/virtualisation/indexes/aggregation) | 00 §9, 06 §8 | queries + models | `tests/perf/*` budgets | 9 | planned |
| R-84 | Honest about practical storage limits (no claim of infinite storage) | 00 §11 | docs + UI text | documentation review | 12 | planned |
| R-85 | Stress testing with realistic large datasets (patients, visits, prescriptions, invoices, payments, attachments, inventory, search, timeline) | 06 §8 | `tools/seed.py` + perf suite | Phase 9 stress report | 9 | planned |
| R-86 | UI does not freeze; long operations show progress and are cancellable where safe | 00 §5, 03 | worker framework | `tests/ui/test_responsiveness.py` | 1, 8, 9 | planned |
| R-87 | Graceful handling of file/path/permission/space/removal/malformed-file errors | 05, 02 §6 | file utilities | `tests/backup/test_failure_paths.py`, attachment error tests | 4, 8 | planned |
| R-88 | Native Windows folder selection, tested | 05 | `QFileDialog` wrapper | UI test + manual checklist | 8 | planned |
| R-89 | Attachments protected from path traversal and unsafe names | 02 §6, 01 §7 | attachment service | `tests/security/test_attachment_safety.py` | 4 | planned |
| R-90 | Local-action security as far as achievable; no frontend-only authorization | 02 | rbac + guards | permission matrix + tamper tests | 2 | planned |
| R-91 | Dependency and licence audit recorded, with third-party notices | 08 | notices + `check_licenses.py` | CI licence job | 1, 10 | planned |
| R-92 | Production build excludes dev dependencies/servers; reproducible to the extent practical | 07 §4 | PyInstaller spec + lock file | packaging tests | 1, 10, 12 | planned |
| R-93 | Organised professional repository structure (UI/domain/data/services/security/printing/backup/config/utils/tests/assets/installer/CI/docs) | 07 §2 | repository layout | structure review | 1 | planned |
| R-94 | No monolithic files; maintainable modules | 07 §2 | module layout | `qa/check_file_sizes.py` (soft cap 700 lines/module, justified exceptions listed) | 10 | planned |
| R-95 | Automated tests at unit/integration/permission/financial/backup-restore/printing/E2E levels | 06 | `tests/*` | coverage gate + suite results | all | planned |
| R-96 | Repeatable acceptance tests for all critical workflows (setup, auth, lock, patients, visits, chart, prescriptions, invoices, payments, inventory, accounting, RBAC, backup, restore, attachments, settings, audit, activation, restart, install, uninstall) | 06 §5 | `tests/acceptance/*` | acceptance matrix results | all | planned |
| R-97 | Formal acceptance-test matrix mapping every major requirement to tests | this repo | `docs/acceptance-test-matrix.md` | matrix reviewed per phase | 0–12 | planned |
| R-98 | Screen-by-screen UI inspection incl. common defect classes and long realistic content | 03 §9 | UI review checklist | Phase 9/11/12 records + goldens | 9, 11, 12 | planned |
| R-99 | Confirmation dialogs for destructive actions and undo/recovery where practical | 03, 05 §7 | dialogs + reversal | `tests/services/test_reversal_paths.py` | 6, 8 | planned |
| R-100 | Patient deletion never destroys financial/clinical history; retention model explicit | 01 §5.4 | soft delete + archive | `tests/services/test_patient_deletion_rules.py` | 4 | planned |
| R-101 | Duplicate patient detection without blocking legitimate families | 01 §5.3 | similarity service | `tests/acceptance/test_duplicate_detection.py` | 4 | planned |
| R-102 | Patient codes unique and stable | 01 §3 | sequence + UNIQUE | integration tests | 2, 4 | planned |
| R-103 | Patient identity safeguards (clear context) in clinical/financial workflows | 03 | patient header strips + confirmation steps | `tests/ui/test_patient_context.py` | 4–6 | planned |
| R-104 | Explicit save/finalize for consequential workflows | 03, 01 §5.2 | draft → finalize pattern | `tests/acceptance/test_finalize_flows.py` | 4–6 | planned |
| R-105 | Unsaved-changes warnings before abandoning forms | 03 §5 | dirty guard | `tests/ui/test_unsaved_guard.py` | 4–6 | planned |
| R-106 | Multi-record transactions (invoice+lines, payment+balance, visit+chart+prescription) | 01 §5.2 | unit of work | `tests/integration/test_transactions.py`, injected failures | 2–6 | planned |
| R-107 | Referential integrity enforced by the database | 01 §5.1 | FKs + pragma | `PRAGMA foreign_key_check` tests | 2 | planned |
| R-108 | Backup completeness verification (data + attachments) | 05 §2 | manifest + hashes | `tests/backup/test_completeness.py` | 8 | planned |
| R-109 | Restore validates compatibility/version before changing data | 05 §4 | manifest validation | `tests/backup/test_version_guard.py` | 8 | planned |
| R-110 | Schema/version mechanism present; incompatible data safely detected | 01 §6 | `app_meta` + user_version | `tests/integration/test_migrations.py` | 2 | planned |
| R-111 | Version displayed in About/diagnostics; deterministic version number | 07 §1 | `version.py` + About | `tests/ui/test_about.py`, version match check | 1, 12 | planned |
| R-112 | Code signing if a certificate is available; otherwise documented honestly | 07 §4 | CI signing step | release notes/report statement | 12 | planned |
| R-113 | GitHub Actions pipeline: install deps, checks, tests, build app, build installer, validate, publish | 07 §5 | `.github/workflows/*` | CI run evidence | 1, 12 | planned |
| R-114 | Final artifact via GitHub Release, else `dist/` with no silent omission | 07 §6 | release workflow + `dist/` | release report | 12 | planned |
| R-115 | PRs are never merged by the agent | 07 §6 | process | PR history review | all | planned |
| R-116 | Logical, non-trivial commit/PR separation per phase | 07 §6 | git history | history review | all | planned |
| R-117 | Phase-by-phase execution with a report at every phase end and no skipping | this repo | `docs/phase-reports/*` | report presence per phase | all | planned |
| R-118 | Accessibility/comfort: keyboard operation, focus visibility, contrast, reduced motion | 03 §8 | design system | a11y checklist tests | 1, 9 | planned |
| R-119 | Data-heavy screens support scrolling/filtering/sorting/pagination/empty states | 03 §4 | DataTable/FilterBar | UI tests + perf tests | 7, 9 | planned |
| R-120 | Screens never silently depend on sample/demo data | 06 §3 | seeding excluded from bundle | packaging test | 1, 12 | planned |

---

## Traceability workflow

1. Every new implementation PR states which requirement ids it advances and marks them `in progress`.
2. A requirement becomes `done` only when its verification entry exists and passes in CI, and the phase
   report records the evidence path.
3. The Phase 12 audit walks this table row by row; any row not `done` blocks the release with a documented
   reason and, where a limitation is unavoidable (e.g. no physical printer in CI), an explicit manual
   verification record replaces the automated evidence.
