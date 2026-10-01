# Dentiva Pro — Formal Acceptance Test Matrix

Each row is an executable acceptance test (`tests/acceptance/…`) with a stable id used in phase reports and
in `docs/requirements-traceability.md`. Manual-only items are marked **[M]** and require a recorded
evidence path (log/screenshot), because no automation can legitimately claim them.

Legend: **A** = automated, **M** = manual/clean-machine, **P** = performance-budgeted.

## A. Installation, activation, first run

| ID | Scenario | Steps (condensed) | Expected result | Type |
|---|---|---|---|---|
| AT-001 | Fresh install | Run installer on clean Windows, default per-user path | Files installed, Start Menu shortcut, entry in Add/Remove Programs, no admin prompt, app launches | M |
| AT-002 | First launch without activation | Start app before activation | Activation wizard shown, no clinic data accessible, cancel exits safely | A |
| AT-003 | Correct activation code | Enter the mandated code | Activated; state file created; about/diagnostics show activation date; no plaintext code anywhere on disk | A |
| AT-004 | Wrong activation code | Enter a wrong code 3× | Uniform error message, ≥ 1 s delay between attempts, audit entries, no crypto detail leaked | A |
| AT-005 | Activation survives restart | Activate, close, reopen, reboot (manual) | Still activated, no re-prompt | A + M |
| AT-006 | Activation state corruption | Corrupt `activation.dat`, reopen | App requests activation again; clinic data untouched and restorable | A |
| AT-007 | First-run setup happy path | Complete the wizard: clinic, logo, address, phone, 2 dentists with multiple designations/qualifications, admin user, currency BDT, printing profile | All entities persisted; admin can log in; clinic identity visible in header; wizard completed flag set | A |
| AT-008 | First-run setup interruption | Kill the process mid-wizard at each step, restart | Wizard resumes or restarts cleanly; **no** half-initialised business data; no partial business rows committed | A |
| AT-009 | Setup atomicity verification | Force a failure on the final transaction (injected) | Database remains empty and consistent; wizard reports the failure | A |
| AT-010 | Post-setup configuration | Change clinic name, logo, add a third dentist, edit qualifications | Changes persist and appear in header/print previews; audited | A |
| AT-011 | Uninstall | Uninstall with default options | Program files/shortcuts/registry removed; clinic data preserved and warning-free | M |
| AT-012 | Reinstall over existing data | Uninstall then reinstall, launch | Existing data intact, no re-setup required, activation persists | M |
| AT-013 | Uninstall removing data | Uninstall with "also remove data" checked | Data folder removed only after explicit confirmation; app cannot silently do this | M |

## B. Authentication, session, RBAC

| ID | Scenario | Steps | Expected | Type |
|---|---|---|---|---|
| AT-020 | Login success/failure | Valid and invalid credentials | Correct session; failures counted and audited; uniform messages | A |
| AT-021 | Lockout & recovery | 5 failures, wait/clear by admin | Account locked for the configured window; admin clear audited | A |
| AT-022 | Auto-lock | Set 5 min, idle | Lock layer covers UI, values masked, background UI timers paused, unlock requires the password | A |
| AT-023 | Sensitive content behind lock | Lock, try keyboard/mouse shortcuts to reach data | No data readable/actionable while locked | A |
| AT-024 | Logout | Logout from session menu | Session ended and audited; login screen; no residue of previous user | A |
| AT-025 | Role permission enforcement (receptionist) | Attempt each finance/admin operation through service and UI | Denied at service layer with audit; UI shows permission-denied states, not blanks | A |
| AT-026 | Permission escalation attempts | Craft service calls and read-model calls without permission; manipulate UI state | All denied before SQL executes; no rows changed; denied events audited | A |
| AT-027 | Role/permission changes take effect | Remove a permission from a role while the user is logged in | Effective at the next operation; UI updates; audit recorded | A |
| AT-028 | Password policy | Try weak/short/username passwords | Rejected with clear guidance; strong password accepted | A |
| AT-029 | Admin password reset | Reset a user's password | Temporary password must be changed at login; audited; no plaintext stored | A |
| AT-030 | Audit coverage | Perform each audited action | Audit row with actor/action/entity/before-after present | A |
| AT-031 | Audit immutability | Attempt UPDATE/DELETE on `audit_log` via SQL | Blocked by trigger; error surfaced to the caller | A |

## C. Patients and clinical workflow

| ID | Scenario | Steps | Expected | Type |
|---|---|---|---|---|
| AT-040 | Register patient | Create with all fields incl. Bengali name/address | Saved with unique code; appears at the top of the default (newest) list; audited | A |
| AT-041 | Validation | Submit with missing required fields / invalid phone | Inline errors, first invalid field focused, nothing saved | A |
| AT-042 | Duplicate detection | Register a second patient with a near-identical name+phone | Warning panel with candidates; user can proceed, open existing, or link as alias; families with similar names are not blocked | A |
| AT-043 | Patient list date filters | Switch Today/7/30/90/1y/custom | Correct result sets, newest first, counts consistent | A |
| AT-044 | Patient search | Search by name (Latin and Bengali), phone, code, address fragment | Relevant results ≤ 250 ms; wrong matches excluded; large dataset | A + P |
| AT-045 | Patient profile | Open a patient with 3 years of history | Overview, contacts, history, timeline, visits, prescriptions, invoices, payments, outstanding, attachments all present; load ≤ 500 ms | A + P |
| AT-046 | Repeated visits | Create 5 visits across dates | Each visit separate and complete; earlier visits unchanged; visit history ordered newest first | A |
| AT-047 | Patient context actions | From the profile create appointment, visit, prescription, invoice, payment, attachment | Patient pre-selected and visible in each drawer; no navigation loss | A |
| AT-048 | Timeline | Open the timeline | Registration, appointments, visits, treatments, prescriptions, invoices, payments, referrals, attachments in chronological order with drill-through | A |
| AT-049 | Attachments | Add image/PDF/text, view, remove; then backup/restore | Stored under UUID names, correct patient link, view works, removal is soft and audited, files restored byte-identically | A |
| AT-050 | Attachment safety | Attempt traversal (`../`), disallowed extension, oversized file, duplicate name | All rejected safely with clear messages | A |
| AT-051 | Dental chart (adult) | Record caries on 36, RCT on 46, missing 18, crown on 11 | Persisted per FDI tooth and per visit; visible on reopen; history per tooth correct | A |
| AT-052 | Dental chart (pediatric) | Switch to primary dentition 51–85, record conditions | Correct numbering and persistence; labels clear; no permanent/primary collision | A |
| AT-053 | Treatment catalog | Create/edit/deactivate treatments with prices and categories; use in a visit and an invoice | Catalogue usable in both; deactivation hides it from new work but keeps history intact | A |
| AT-054 | Snapshot integrity | Rename a treatment and change its price after an old visit/invoice | Old documents show the original name/price; new ones use current values | A |
| AT-055 | Referral | Record a referral with destination, reason, follow-up | Stored, visible in profile timeline and referral list | A |
| AT-056 | Patient archival | Archive a patient with history | Hidden from default lists, still searchable with badge, history and finance intact | A |
| AT-057 | Permanent delete guard | Attempt permanent delete on a patient with dependents | Refused with an explanation; audit shows the attempt | A |
| AT-058 | Large patient dataset | 50 000 patients, list/search/paginate/profile open | Within budgets; UI responsive; memory bounded | A + P |

## D. Appointments, queue, prescriptions, printing

| ID | Scenario | Steps | Expected | Type |
|---|---|---|---|---|
| AT-070 | Appointment creation | Create with patient, dentist, date, time, duration, reason | Saved with unique code; appears in the day list and calendar | A |
| AT-071 | Conflict handling | Book the same dentist overlapping | Blocked (or warned) per the configured rule, with a clear message; audited | A |
| AT-072 | Appointment lifecycle | Confirm → check in → in progress → completed; and cancel/no-show | Statuses correct, timestamps recorded, queue/visit linkage correct | A |
| AT-073 | Queue workflow | Add walk-in and appointment patients, call, start consultation, complete | Token ordering respected; dentist-specific queues filter correctly; statuses synchronise with visits | A |
| AT-074 | Prescription with many medicines | Create a prescription with 8 medicines, mixed formulations, doses, food relations, durations, instructions; reorder; remove one | All data preserved, order respected, no data loss on edit | A |
| AT-075 | Structured findings | Select several C/C and O/E findings, add Dx and advice (structured + free text) | Persisted structurally, rendered in the correct sections, catalogue-configurable | A |
| AT-076 | Prescription finalisation | Finalise and print | Explicit finalize action; header snapshot captured; reprint identical | A |
| AT-077 | Prescription print A4 | Print preview + PDF export | Premium layout, all identity blocks complete, ≥ 22 mm signature area, page count as expected, no clipping | A |
| AT-078 | Prescription print A5 / thermal 58 / 80 mm | Render each profile with long content | No overlap/clipping; table stays readable; thermal template single-column | A |
| AT-079 | Long-content printing | 25 medicines, 300-char Bengali note, 6 qualifications, 80-char patient name | Continuation pages with repeated headers; nothing clipped; signature area preserved on the last page | A |
| AT-080 | Bengali print fidelity | Prescription/invoice with Bengali text | Correct shaping, no boxes, fonts embedded in the PDF | A |
| AT-081 | Printer failure handling | Simulate unsupported page size and a device error | Plain-language dialog with options; no broken output; logged with correlation id | A |
| AT-082 | Print permission | Attempt to print/finalise without permission | Denied at service layer and audited; UI shows a denied state | A |
| AT-083 | Determinism | Render the same prescription twice | Identical page geometry and text content | A |

## E. Billing, payments, inventory, accounting

| ID | Scenario | Steps | Expected | Type |
|---|---|---|---|---|
| AT-100 | Invoice creation | Create from a visit with treatment lines, quantities, discounts | Exact totals (Decimal/paisa); status UNPAID; code unique; audited | A |
| AT-101 | Invoice finalisation atomicity | Inject a failure while writing lines | Nothing persisted (no orphan invoice/line); error surfaced | A |
| AT-102 | Partial payment | Pay half of a ৳ 12,450.75 invoice | Status PARTIALLY PAID; balance exact; payment row separate; invoice totals unchanged | A |
| AT-103 | Multiple payments and settlement | Add further payments incl. overpayment attempt | Balance reaches zero → PAID; overpayment blocked or explicitly handled per settings; full history listed | A |
| AT-104 | Payment methods | Cash, bank, card, bKash, Nagad, Rocket, Upay, other with reference numbers | Stored correctly; method summary reports correct | A |
| AT-105 | Payment reports | Today/7/30/90/1y/custom | Totals and method breakdowns match the ledger exactly | A |
| AT-106 | Voiding a payment | Void with a reason | Payment marked voided, invoice balance recalculated, audit records before/after, original row retained | A |
| AT-107 | Invoice void/adjustment | Void an invoice, add a correction and a write-off path | Posted history preserved; corrections additive; balances consistent | A |
| AT-108 | Financial immutability | Attempt direct update of posted totals via SQL | Blocked by design/tests; only service-level adjustments allowed | A |
| AT-109 | Financial permission enforcement | Receptionist/assistant attempts reports, accounting, payment lists, balances | Denied in the service layer and in query guards; dashboard shows no financial leaks | A |
| AT-110 | Inventory purchase | Receive stock with batch, expiry, cost, supplier | Movement recorded; stock increases; batch tracked; expense link correct | A |
| AT-111 | Inventory usage | Consume stock against a visit | Movement recorded; stock decreases; patient/visit link present | A |
| AT-112 | Inventory adjustment & reconciliation | Adjust, write off expired stock; run integrity check | Stock equals the sum of movements; discrepancies reported, never silently "fixed" | A |
| AT-113 | Low-stock alert | Drop stock below the threshold | Alert in inventory and notification centre; respects inventory cost permission | A |
| AT-114 | Expiry alert | Batch expiring within the configured window | Alert with item, batch, expiry, quantity | A |
| AT-115 | Expense entry | Record rent/electricity/supplies/salary/maintenance/misc | Auditable entry; included in expense reports; categories configurable | A |
| AT-116 | Financial reports | Daily/weekly/monthly/quarterly/yearly/custom | Income, expenses, collections, receivables consistent with underlying rows; numbers exact | A |
| AT-117 | Invoice printing | A4 and thermal with many lines and long descriptions | Totals correct, status stamp correct, no clipping, page totals correct | A |
| AT-118 | Financial rounding stress | 10 000 random line sets | Sum of lines + adjustments equals stored total exactly; no float artefacts | A |

## F. Dashboard, search, notifications, settings, data safety

| ID | Scenario | Steps | Expected | Type |
|---|---|---|---|---|
| AT-130 | Dashboard widgets | Load with a realistic dataset as admin | Appointments, queue, new patients, visits, receivables, low stock, upcoming, recent activity all correct and fast | A + P |
| AT-131 | Dashboard permission awareness | Load as a user without financial permissions | No financial values anywhere (cards, charts, tooltips, exports, notifications) | A |
| AT-132 | Global search | Search across entities with mixed permissions | Correct, typed results with context; restricted entities absent for unauthorised users | A |
| AT-133 | Notification centre | Trigger appointment/inventory/backup/security events | Deduplicated, permission-filtered, readable, non-noisy; unread badge correct | A |
| AT-134 | Settings changes | Change auto-lock, print profile, numbering prefixes, thresholds | Applied immediately where applicable; audited with before/after; validation prevents invalid values | A |
| AT-135 | Destructive guards | Attempt "delete all data" without permission / without phrase / without backup | Refused at each stage with clear explanations; the successful path requires the typed phrase and is audited | A |
| AT-136 | Manual backup | Choose a folder via the native dialog, run backup | Deterministic filename, container with DB + attachments + manifest, self-check passes, run recorded | A |
| AT-137 | Automatic backup | Configure 7/15/30 days, simulate the due date | Runs and records; missed schedules reported honestly; retention keeps the newest N | A |
| AT-138 | Backup failure paths | Not writable, insufficient space, device removed, cancel mid-run | Specific errors, no complete-looking file, live data untouched, honest status | A |
| AT-139 | Backup completeness | Verify manifest vs DB vs attachments | Counts and hashes match; missing attachment files reported as findings | A |
| AT-140 | Restore happy path | Restore a backup after modifying data | Pre-restore safety backup created; data matches the backup exactly; sessions invalidated; audit + run records | A |
| AT-141 | Restore validation failure | Corrupt/truncate the container, tamper a hash | Restore refused before any change; live data untouched; clear message | A |
| AT-142 | Restore commit failure | Inject a failure during the swap | Automatic rollback; original data intact; both paths reported | A |
| AT-143 | Version guards | Restore a newer-schema backup; restore an older one | Newer refused with explanation; older migrated safely with a pre-migration backup | A |
| AT-144 | Integrations after restore | Print a prescription and an invoice from restored data | Documents render identically to before the backup | A |
| AT-145 | Diagnostics export | Export a diagnostics pack | Contains versions/logs/integrity/counts; contains no patient clinical content, passwords or activation data | A |
| AT-146 | Offline operation | Disconnect all network interfaces, run the full daily workflow | Everything works (no network calls); verified by a request monitor during the run | A |

## G. Cross-cutting quality

| ID | Scenario | Expected | Type |
|---|---|---|---|
| AT-160 | Full clinic day workflow | Registration → appointment → queue → visit → chart → treatment → prescription → print/PDF → invoice → partial payment → later payment → accounting → follow-up → timeline all correct and linked | A |
| AT-161 | Multi-user day | Two dentists plus receptionist and billing officer concurrently (separate sessions) | No cross-permission leaks; data consistency maintained; no lock contention failures | A |
| AT-162 | High-DPI | 100/125/150/175/200 % scaling on 4 viewport sizes | No blur (up to Qt's fractional-scaling limits), clipping, overlap or microscopic text; goldens reviewed | A + M |
| AT-163 | State coverage | Every route/screen exposes loading, empty, error, denied, disabled, selected, focus, hover, dirty, saved states | No blank or broken screens | A |
| AT-164 | Keyboard-only operation | Complete the main workflows using only the keyboard | Achievable, focus visible, shortcuts documented and non-conflicting | A |
| AT-165 | Long-content UI | Tables/forms/dialogs with extreme real-world content | No clipping/overlap/overflow; ellipsis with tooltips where intended | A |
| AT-166 | Performance budgets | Startup, login, lists, profile, dashboard, preview, save, backup | Within documented budgets on the reference dataset | A + P |
| AT-167 | Stress | 50 k patients / 300 k clinical+financial rows / 5 k attachments / 5-year history | Stable memory, responsive UI, no freezes, budgets met | A + P |
| AT-168 | No placeholders | Static scans and manual review of every screen | No TODO, mock, dummy, coming-soon, dead control or non-functional button | A + M |
| AT-169 | Dependency/licence audit | Lock file vs notices vs bundle contents | All licensed correctly; no dev-only packages; notices shipped | A |
| AT-170 | Secret scan | Scan source, bundle, installer, logs, docs for the activation code and derived constants in multiple encodings | Not found | A |
| AT-171 | Clean-machine end-to-end | Install → activate → setup → restart → login → lock → patient/clinical/financial flows → print → PDF → backup → restore → attachment → settings → uninstall → reinstall | Every step passes with recorded evidence | M |

## Execution policy

- AT-001…AT-170 automated items run in CI per phase; AT-171 and the `M` items are executed at Phase 17 on a
  clean Windows environment with a written evidence record (screenshots/log paths) stored in
  `docs/phase-reports/phase-17/evidence/`.
- A phase cannot be declared complete while any automated acceptance test in its scope fails.
- Any waiver requires an explicit, documented justification approved by the user; silent downgrades are
  not permitted.
