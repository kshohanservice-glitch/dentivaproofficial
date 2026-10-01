# Dentiva Pro — Domain Model and Database Architecture (Phase 0)

Database: **SQLite 3** (file `dentivapro.db`), `journal_mode=WAL`, `foreign_keys=ON`,
`synchronous=NORMAL`, `busy_timeout=5000`, `temp_store=MEMORY`.
All schema DDL lives in `src/dentivapro/data/schema/*.sql` and is applied transactionally by
`data/db/migrations.py` with a `schema_version` recorded in both `PRAGMA user_version` and `app_meta`.

---

## 1. Global conventions

| Convention | Rule |
|---|---|
| Primary keys | Surrogate `INTEGER PRIMARY KEY` (rowid alias) for entities; `TEXT` natural keys only for catalogues/permissions |
| Business codes | Human-readable, unique, generated inside the owning transaction from the `sequence` table (no `MAX()+1`, collision-safe under concurrency), immutable once issued |
| Money | `*_minor INTEGER NOT NULL` = amount × 100 (paisa). Domain type `Money(Decimal)`; SQLite does exact integer arithmetic. **No floats anywhere in the money path** |
| Quantities | `*_milli INTEGER` = quantity × 1000 (supports 2.5 ml, 0.5 box, 1 strip without float drift) |
| Instants | `*_at` columns = UTC ISO-8601 text (`YYYY-MM-DDTHH:MM:SSZ`) |
| Business dates | `*_on` / `*_date` columns = clinic-local calendar date (`YYYY-MM-DD`) |
| Booleans | `INTEGER NOT NULL DEFAULT 0 CHECK (x IN (0,1))` |
| Enumerations | `TEXT` with `CHECK (col IN (...))` — readable in the DB, validated in Python too |
| Audit metadata | every mutable business table carries `created_at`, `created_by`, `updated_at`, `updated_by` (`*_by` = user id, FK RESTRICT, plus a username snapshot column where the row must survive user removal) |
| Soft delete | `is_active` / `deleted_at` + `deleted_by` + `delete_reason`; hard `DELETE` is not used on business records |
| Snapshots | Documents that are printed or posted store a `*_snapshot` JSON column (clinic letterhead, dentist identity, patient identity, catalogue names/prices) captured when finalised so history never mutates when configuration changes |
| Naming | `snake_case`, singular table names, `<entity>_id` for FKs, `<entity>_code` for business codes |

---

## 2. Entity catalogue

### 2.1 System and configuration

| Table | Key columns | Notes |
|---|---|---|
| `app_meta` | `key TEXT PK`, `value TEXT`, `updated_at` | schema_version, app_version, installation_id, first_run_completed_at, activated_at, activated_by_code_fingerprint (a *derived* fingerprint, never the code) |
| `settings` | `key TEXT PK`, `value TEXT`, `updated_at`, `updated_by` | Typed registry in code; sensitive keys flagged; every change audited with before/after |
| `sequence` | `name TEXT PK`, `prefix TEXT`, `padding INTEGER`, `next_value INTEGER` | Allocates patient/appointment/visit/Rx/invoice/payment/expense/movement codes inside the consumer's transaction |
| `clinic` | single row `CHECK(id=1)`: `name`, `name_bn`, `legal_name`, `address`, `address_bn`, `phone`, `phone_alt`, `email`, `website`, `logo_relpath`, `tin`, `bin`, `currency_code='BDT'`, `footer_note`, `hours_note`, `created_at`, `updated_at` | Invoice/prescription letterhead source (snapshotted per document) |
| `machine_registry` | `installation_id TEXT PK`, `first_seen_at`, `last_seen_at`, `app_version`, `machine_label` | Supports restore-on-another-machine detection and diagnostics |

### 2.2 People: dentists, staff, users, roles

| Table | Key columns | Notes |
|---|---|---|
| `dentist` | `id`, `code UNIQUE`, `full_name`, `full_name_bn`, `phone`, `email`, `bmdc_reg_no`, `specialization`, `signature_relpath`, `is_active`, `display_order`, `created_at`, `updated_at`, `deleted_at` | Multiple dentists natively supported; never hard-deleted if referenced |
| `designation` | `id`, `name UNIQUE`, `sort_order`, `is_active` | e.g. "Consultant Dental Surgeon", "Assistant Professor" |
| `dentist_designation` | `dentist_id`, `designation_id`, `sort_order`, PK(dentist_id, designation_id) | **Multiple designations per dentist** |
| `qualification` | `id`, `name UNIQUE`, `sort_order`, `is_active` | e.g. "BDS", "MDS (Oral & Maxillofacial Surgery)", "FCPS", "PhD" |
| `dentist_qualification` | `dentist_id`, `qualification_id`, `sort_order`, PK(dentist_id, qualification_id) | **Multiple qualifications per dentist**, rendered in order on prescriptions |
| `staff` | `id`, `code UNIQUE`, `full_name`, `phone`, `email`, `role_id`, `user_id NULL`, `joined_on`, `is_active`, `notes` | A staff member may exist without a login |
| `role` | `id`, `code UNIQUE`, `name`, `description`, `is_system`, `is_admin`, `sort_order`, `is_active` | Seeded roles + custom roles |
| `permission` | `code TEXT PK`, `area`, `name`, `description`, `is_sensitive` | Canonical catalogue (see `02-security-and-rbac.md`) |
| `role_permission` | `role_id`, `permission_code`, `allowed`, PK(role_id, permission_code) | Role grants |
| `user_permission_override` | `user_id`, `permission_code`, `allowed`, `reason`, `granted_by`, `granted_at`, PK(user_id, permission_code) | Per-user exceptions; overrides win over role grants |
| `user` | `id`, `username UNIQUE COLLATE NOCASE`, `display_name`, `email`, `phone`, `password_hash`, `password_algo`, `password_updated_at`, `must_change_password`, `role_id`, `dentist_id NULL`, `staff_id NULL`, `is_active`, `is_locked`, `failed_attempts`, `locked_until`, `last_login_at`, `created_at`, `updated_at`, `deleted_at` | Never stores plaintext passwords; Argon2id strings only |
| `session` | `id TEXT PK (uuid)`, `user_id`, `started_at`, `last_seen_at`, `locked_at`, `ended_at`, `end_reason`, `app_version` | Session lifecycle, auto-lock and audit correlation |
| `login_attempt` | `id`, `username_tried`, `at_utc`, `success`, `reason`, `machine_label` | Survives user deletion (no FK) for security forensics |

### 2.3 Patients and clinical core

| Table | Key columns | Notes |
|---|---|---|
| `patient` | `id`, `code UNIQUE`, `full_name`, `name_bn`, `gender CHECK(in male,female,other,unknown)`, `dob`, `age_years`, `age_recorded_on`, `blood_group`, `phone`, `phone_alt`, `email`, `address`, `address_bn`, `national_id`, `occupation`, `marital_status`, `emergency_name`, `emergency_relation`, `emergency_phone`, `guardian_name`, `chief_complaint`, `medical_history`, `allergies`, `referred_by`, `notes`, `is_active`, `is_archived`, `created_at/by`, `updated_at/by`, `deleted_at/by`, `delete_reason`, `search_blob` | Practically unlimited rows; `search_blob` is a normalised (lower-cased, Bangla-normalised, whitespace-collapsed) concatenation maintained by the repository on write to make search fast and deterministic |
| `patient_alias` | `alias_patient_id PK`, `primary_patient_id`, `linked_by`, `linked_at`, `reason` | Handles accidental duplicates **without moving clinical/financial history** (see §5.3) |
| `patient_note` | `id`, `patient_id`, `category`, `body`, `created_at/by`, `is_deleted` | Free-form longitudinal notes (phone calls, recalls) |
| `attachment` | `id`, `uuid UNIQUE`, `patient_id`, `visit_id NULL`, `kind CHECK(in prescription,report,xray,photo,consent,other)`, `original_name`, `stored_relpath`, `mime`, `size_bytes`, `sha256`, `caption`, `uploaded_at/by`, `is_deleted`, `deleted_at/by` | File payloads live in the file store, never in the DB |
| `referral` | `id`, `code UNIQUE`, `patient_id`, `visit_id NULL`, `direction CHECK(in out,in)`, `to_doctor`, `to_org`, `to_phone`, `reason`, `clinical_summary`, `referred_on`, `follow_up_on`, `status`, `notes`, `created_at/by` | Appears in the patient timeline |
| `clinical_finding_catalog` | `id`, `kind CHECK(in complaint,examination,diagnosis,recommendation)`, `code UNIQUE`, `label`, `label_bn`, `is_active`, `is_system`, `sort_order` | Seeded with the clinically requested defaults (pain, generalized caries, swelling, gum bleeding, bad breath, sensitivity, caries, gingival caries, BDR/BDC, gingivitis, periodontal pocket, periodontitis, pulpitis, impacted teeth, dry socket, attrition, erosion, …) and fully configurable afterwards |
| `tooth_condition_catalog` | `code PK`, `label`, `label_bn`, `color_hex`, `is_active`, `sort_order` | Caries, filled, missing, crown, RCT, implant, impacted, fractured, mobile, pocket depth markers, … |
| `treatment_category` | `id`, `name UNIQUE`, `sort_order`, `is_active` | e.g. Restorative, Endodontic, Surgical, Orthodontic, Prosthodontic |
| `treatment_catalog` | `id`, `code UNIQUE`, `name`, `name_bn`, `category_id`, `default_price_minor`, `duration_minutes`, `description`, `is_active`, `created_at/by`, `updated_at/by` | Usable from both visits and billing |
| `medicine_catalog` | `id`, `name`, `formulation`, `strength`, `default_dose_morning/noon/night`, `default_relation_to_food`, `default_duration_days`, `default_instructions`, `is_favorite`, `usage_count`, `is_active` | Speeds up prescription entry; free text always allowed |
| `visit` | `id`, `code UNIQUE`, `patient_id`, `appointment_id NULL`, `dentist_id`, `visit_date`, `started_at`, `closed_at`, `chief_complaint`, `history`, `examination`, `diagnosis`, `advice`, `follow_up_on`, `status CHECK(in open,closed,voided)`, `void_reason`, `notes`, `created_at/by`, `updated_at/by` | One row per clinic visit; a new visit never overwrites a previous one |
| `visit_finding` | `id`, `visit_id`, `kind`, `finding_id NULL`, `label_snapshot`, `note`, `sort_order` | Structured + free-text clinical content |
| `visit_treatment` | `id`, `visit_id`, `treatment_id NULL`, `name_snapshot`, `category_snapshot`, `unit_price_minor_snapshot`, `quantity_milli`, `status CHECK(in planned,performed,advised,cancelled)`, `teeth_json`, `note`, `sort_order`, `created_at/by` | Snapshot columns keep history stable if the catalogue is renamed or re-priced |
| `tooth_record` | `id`, `patient_id`, `visit_id NULL`, `dentition CHECK(in permanent,primary)`, `fdi_no INTEGER`, `status_code`, `notes`, `recorded_at/by`, UNIQUE(patient_id, visit_id, dentition, fdi_no) | **Structurally persisted** dental chart (not a screenshot); FDI numbering for permanent (11–48) and primary (51–85) dentition |
| `prescription` | `id`, `code UNIQUE`, `patient_id`, `dentist_id`, `visit_id NULL`, `issued_on`, `issued_at`, `status CHECK(in draft,final,void)`, `cc_note`, `oe_note`, `re_advice`, `diagnosis_summary`, `follow_up_on`, `header_snapshot` JSON, `footer_snapshot` JSON, `print_count`, `last_printed_at`, `void_reason`, `created_at/by`, `updated_at/by` | Header/footer snapshots make reprints deterministic |
| `prescription_item` | `id`, `prescription_id`, `sort_order`, `medicine_name`, `formulation`, `strength`, `dose_morning/noon/night/other`, `relation_to_food CHECK(in before,after,with,na)`, `duration_value`, `duration_unit CHECK(in day,week,month,continue)`, `quantity`, `instructions`, `is_prn` | Multiple medicines, reorderable, never silently dropped |
| `prescription_finding` | `id`, `prescription_id`, `kind CHECK(in cc,oe,dx,advice)`, `finding_id NULL`, `label_snapshot`, `note`, `sort_order` | Structured selections + free text for C/C, O/E, R/E/Advice |

### 2.4 Appointments, queue

| Table | Key columns | Notes |
|---|---|---|
| `appointment` | `id`, `code UNIQUE`, `patient_id`, `dentist_id`, `scheduled_on` (local date), `start_minute` (minutes from midnight), `duration_minutes`, `reason`, `notes`, `status CHECK(in scheduled,confirmed,checked_in,in_progress,completed,cancelled,no_show)`, `cancel_reason`, `checked_in_at`, `completed_at`, `created_at/by`, `updated_at/by` | Conflict detection over (dentist, date, interval) at the service layer, configurable block/warn |
| `queue_entry` | `id`, `patient_id`, `appointment_id NULL`, `dentist_id NULL`, `visit_id NULL`, `token_no`, `status CHECK(in waiting,called,in_consultation,completed,skipped,cancelled)`, `priority`, `entered_at`, `called_at`, `started_at`, `completed_at`, `notes`, `created_at/by` | Token numbers are per-clinic-per-day, allocated from `sequence` with a daily reset |

### 2.5 Billing and accounting

| Table | Key columns | Notes |
|---|---|---|
| `invoice` | `id`, `code UNIQUE`, `patient_id`, `visit_id NULL`, `dentist_id NULL`, `issue_date`, `issued_at`, `status CHECK(in draft,final,partially_paid,paid,void,written_off)`, `subtotal_minor`, `discount_minor`, `surcharge_minor`, `total_minor`, `paid_minor`, `balance_minor`, `note`, `header_snapshot` JSON, `footer_snapshot` JSON, `finalized_at`, `void_reason`, `voided_at/by`, `created_at/by`, `updated_at/by` | Totals cached for list performance and re-verified by an integrity job; `balance_minor` is always `total - paid` |
| `invoice_line` | `id`, `invoice_id`, `sort_order`, `item_type CHECK(in treatment,product,service,other)`, `treatment_id NULL`, `inventory_item_id NULL`, `description`, `description_bn`, `quantity_milli`, `unit_price_minor`, `line_discount_minor`, `line_total_minor`, `teeth_json`, `note` | Totals computed in `Money` and stored exactly |
| `invoice_adjustment` | `id`, `invoice_id`, `kind CHECK(in discount,surcharge,write_off,correction)`, `amount_minor`, `reason`, `created_at/by` | Corrections are *appended*, never a silent rewrite of posted totals |
| `payment` | `id`, `code UNIQUE`, `patient_id`, `invoice_id`, `amount_minor`, `method CHECK(in cash,bank,card,bkash,nagad,rocket,upay,other)`, `reference_no`, `received_on`, `received_at`, `status CHECK(in posted,voided)`, `note`, `void_reason`, `voided_at/by`, `created_at/by`, `patient_name_snapshot`, `invoice_code_snapshot` | Multiple payments per invoice; each is immutable once posted (void + re-issue instead) |
| `expense_category` | `id`, `name UNIQUE`, `is_system`, `is_active`, `sort_order` | Seeded: clinic rent, electricity, internet, supplies/accessories, staff salary, maintenance, miscellaneous |
| `expense` | `id`, `code UNIQUE`, `category_id`, `amount_minor`, `spent_on`, `paid_to`, `method`, `reference_no`, `note`, `attachment_id NULL`, `status CHECK(in posted,voided)`, `void_reason`, `created_at/by` | Auditable, voidable, never silently edited after posting |
| `other_income` | `id`, `code UNIQUE`, `source`, `amount_minor`, `received_on`, `method`, `reference_no`, `note`, `status`, `void_reason`, `created_at/by` | Non-invoice income (lab refunds, insurance) so reports are honest |

### 2.6 Inventory

| Table | Key columns | Notes |
|---|---|---|
| `supplier` | `id`, `name`, `contact_person`, `phone`, `email`, `address`, `note`, `is_active` | |
| `inventory_category` | `id`, `name UNIQUE`, `sort_order`, `is_active` | Consumables, instruments, materials, PPE, … |
| `inventory_item` | `id`, `sku UNIQUE NULL`, `name`, `name_bn`, `category_id`, `unit`, `supplier_id NULL`, `min_stock_milli`, `current_stock_milli` (cache), `last_purchase_price_minor`, `is_active`, `note`, `created_at/by`, `updated_at/by`, `deleted_at` | `current_stock_milli` is **only** changed by inventory movements inside the same transaction, and reconciled by a verification query |
| `inventory_batch` | `id`, `item_id`, `batch_no`, `expiry_on`, `qty_received_milli`, `qty_remaining_milli`, `unit_cost_minor`, `supplier_id`, `received_on`, `note` | Batch/lot + expiry tracking |
| `inventory_movement` | `id`, `code UNIQUE`, `item_id`, `batch_id NULL`, `kind CHECK(in purchase,usage,adjustment_in,adjustment_out,return_in,return_out,expired_write_off,lost,reversal)`, `qty_milli` (signed), `unit_cost_minor`, `moved_on`, `visit_id NULL`, `patient_id NULL`, `expense_id NULL`, `reversal_of_id NULL`, `reason`, `note`, `created_at/by` | Append-only ledger; stock is provably the sum of movements; void = reversal row |

### 2.7 Security, audit, notifications, maintenance

| Table | Key columns | Notes |
|---|---|---|
| `audit_log` | `id`, `at_utc`, `actor_user_id NULL`, `actor_username`, `session_id`, `action`, `entity_type`, `entity_id`, `entity_code`, `summary`, `before_json`, `after_json`, `severity CHECK(in info,notice,warning,critical)`, `machine_label`, `app_version`, `correlation_id` | Append-only (enforced by `BEFORE UPDATE`/`BEFORE DELETE` triggers that `RAISE(ABORT)`), indexed by time/entity/action; visible to `audit.view` holders |
| `notification` | `id`, `created_at`, `kind`, `severity`, `title`, `body`, `entity_type`, `entity_id`, `required_permission NULL`, `target_user_id NULL`, `dedupe_key UNIQUE`, `is_read`, `read_at`, `expires_at` | Notification centre; `required_permission` gates visibility (no financial leaks) |
| `maintenance_run` | `id`, `kind CHECK(in backup,restore,integrity_check,vacuum,export,index_rebuild)`, `started_at`, `finished_at`, `status CHECK(in running,success,failed,cancelled)`, `target_path`, `bytes`, `message`, `checksum`, `rows_affected`, `performed_by`, `is_automatic` | Backup/restore history and status shown in the UI |
| `backup_schedule` | `id` (single row), `enabled`, `interval_days CHECK(in 7,15,30)`, `target_folder`, `last_run_at`, `next_run_at`, `keep_last_n`, `include_attachments`, `updated_at/by` | Automatic backups |
| `integrity_finding` | `id`, `checked_at`, `code`, `severity`, `entity_type`, `entity_id`, `detail`, `resolved_at` | Output of integrity jobs (stock mismatches, orphan files, balance mismatches) |

---

## 3. Identifier strategy

| Entity | Format | Example | Notes |
|---|---|---|---|
| Patient | `P-` + 6 digits | `P-000042` | Never reused, allocated transactionally |
| Appointment | `AP-yymm-` + 5 digits | `AP-2610-00007` | Month-scoped readability |
| Visit | `V-yymm-` + 5 digits | `V-2610-00031` | |
| Prescription | `RX-yymm-` + 5 digits | `RX-2610-00118` | |
| Invoice | `INV-yymm-` + 5 digits | `INV-2610-00094` | Configurable prefix/suffix in Settings (e.g. clinic TIN) but the default is deterministic |
| Payment | `PMT-yymm-` + 5 digits | `PMT-2610-00090` | |
| Expense | `EXP-yymm-` + 5 digits | `EXP-2610-00012` | |
| Other income | `INC-yymm-` + 5 digits | `INC-2610-00003` | |
| Inventory movement | `IMV-yymm-` + 6 digits | `IMV-2610-000231` | |
| Referral | `REF-yymm-` + 4 digits | `REF-2610-0009` | |
| Dentist / Staff / User / Role | `DR-###`, `ST-###`, `USR-###`, role code | `DR-001`, `USR-003` | |
| Document verification | `DOC-<sha1-12>` | `DOC-9f2c…` | Optional QR content on printed documents |

`sequence` rows are updated with `UPDATE sequence SET next_value = next_value + 1 WHERE name = ?`
inside the same transaction that inserts the business row; the read of the new value is the `RETURNING`
result. Codes are therefore unique and collision-safe even under concurrent writers, and gaps are
acceptable (never reused).

---

## 4. Index plan (hot paths)

- `patient(search_blob)`, `patient(phone)`, `patient(code)`, `patient(full_name COLLATE NOCASE)`,
  `patient(created_at DESC)`, `patient(is_archived, is_active)`
- `appointment(scheduled_on, start_minute)`, `appointment(dentist_id, scheduled_on)`, `appointment(status)`
- `queue_entry(status, entered_at)`, `queue_entry(dentist_id, status)`
- `visit(patient_id, visit_date DESC)`, `visit(dentist_id, visit_date DESC)`, `visit(status)`
- `visit_treatment(visit_id)`, `tooth_record(patient_id, dentition)`, `tooth_record(visit_id)`
- `prescription(patient_id, issued_on DESC)`, `prescription(dentist_id, issued_on DESC)`, `prescription(code)`
- `payment(patient_id, received_on DESC)`, `payment(received_on)`, `payment(invoice_id)`, `payment(method, received_on)`
- `invoice(patient_id, issue_date DESC)`, `invoice(status, issue_date)`, `invoice(issue_date)`
- `expense(spent_on)`, `expense(category_id, spent_on)`, `other_income(received_on)`
- `inventory_item(category_id, is_active)`, `inventory_batch(item_id, expiry_on)`, `inventory_movement(item_id, moved_on DESC)`
- `audit_log(at_utc DESC)`, `audit_log(entity_type, entity_id)`, `audit_log(action, at_utc DESC)`, `audit_log(actor_user_id, at_utc DESC)`
- `notification(is_read, created_at DESC)`, `notification(dedupe_key)`
- `attachment(patient_id, is_deleted)`, `attachment(sha256)`

List screens use **keyset pagination** (`WHERE (sort_key, id) < (?, ?) ORDER BY … LIMIT n`) so deep
pages stay O(log n); `COUNT(*)` is only computed when the user asks for totals, and heavy counts are
served from cached aggregates maintained by the writing services.

---

## 5. Integrity, lifecycle and deletion rules

### 5.1 Referential integrity
All foreign keys are declared and enforced (`ON DELETE RESTRICT` for historical references,
`ON DELETE CASCADE` only for pure child collections such as `invoice_line`, `prescription_item`,
`visit_finding`, `visit_treatment`, `tooth_record`, `queue_entry` → parent). `PRAGMA foreign_key_check`
runs during every integrity check and every restore.

### 5.2 Transaction boundaries (must be atomic)
- Patient registration (+ initial note + code allocation)
- Visit creation with findings + treatments + tooth records
- Prescription finalisation with all items + findings
- Invoice finalisation with lines + adjustments and cached totals
- Payment posting (+ invoice cached paid/balance + status transition)
- Inventory movement (+ batch remaining + item stock cache + optional expense)
- Backup run record, restore run record, settings changes, role/permission changes
- First-run setup completion (clinic + dentists + designations + qualifications + admin user + settings +
  `first_run_completed_at`) — a single transaction, so an interrupted setup leaves an empty DB with a
  resumable wizard rather than half-initialised business data.

### 5.3 Duplicate patients
On registration the service computes a similarity score over normalised name + phone + date of birth
(+ guardian for minors) and, above a configurable threshold, shows a "possible duplicate" panel listing
candidates with their codes, phones and last visit. The user may (a) open the existing patient,
(b) proceed (family members with similar names are legitimate), or (c) link the new record as an alias
of the primary one (`patient_alias`) — which shows the relationship in both profiles without moving any
clinical or financial history. No automatic merging is performed, because merging financial history
silently would break auditability.

### 5.4 Deletion and retention
| Entity | Policy |
|---|---|
| Patient | Archive only (soft). Archived patients disappear from default lists, remain searchable with an "archived" badge, keep every document and payment. Hard delete is **not** implemented — it would destroy legally relevant financial/clinical history. Where a record was created in error on day one with no dependent rows, an admin-only "delete permanently" path exists with typed confirmation and audit; it is refused if any dependent row exists |
| User / staff / dentist | Deactivate (`is_active=0`); never deleted while referenced. Historical documents keep name snapshots |
| Visit / prescription / invoice / payment / expense / movement | Void/cancel with reason + audit; never edited after posting; corrections are additive adjustments or reversal rows |
| Attachments | Soft delete (file moved to `attachments/.trash/<uuid>`, row flagged); purge only via an explicit admin maintenance action, itself audited |
| Treatment / finding / medicine catalogues | Deactivate, never delete; historical rows hold snapshots |
| Audit log | Never deleted by the application; no UI path modifies it |

### 5.5 Verification jobs
`services/maintenance.py` implements, and Settings → Data exposes with progress and results:
`PRAGMA integrity_check` + `foreign_key_check`; invoice `total = Σ lines + Σ adjustments` and
`balance = total − paid`; `invoice.status` consistent with paid/balance; inventory
`current_stock = Σ movements` and `batch.qty_remaining = Σ batch movements`; orphan attachment files
and orphan attachment rows; patients with duplicate codes (must be zero); audit log immutability smoke
test. Findings are written to `integrity_finding` and are never auto-fixed silently — each fix is an
explicit, audited action.

---

## 6. Schema versioning and forward safety

- `app_meta.schema_version` + `PRAGMA user_version` hold the integer schema version.
- Migrations are ordered, transactional and idempotent; before any migration that changes data the app
  takes an automatic pre-migration backup into `<data root>/backups/`.
- If the DB reports a **newer** schema than the app supports, the app refuses to open it, explains the
  situation in plain language, and offers backup/export/restore paths instead of mutating data.
- Because v1.0.0 is the final release line, migrations exist primarily for safety (restored old
  backups, partial installs), not for ongoing feature upgrades.

---

## 7. Attachment storage design

- Files are stored as `<data root>/attachments/<patient_id>/<uuid>.<sanitised-ext>`; the database keeps
  the original filename, MIME type, size and SHA-256.
- Filenames from users never touch the filesystem: extension is validated against an allow-list,
  a UUID is generated for the stored name, and the original name is preserved only as data.
- Path traversal is impossible by construction (no user string is joined into a path); the service
  additionally resolves the final path and asserts it stays under the attachments root.
- Add/remove is permission-gated (`patient.attachment.*`) and audited; size limits and per-patient
  counts are configurable with sane defaults (25 MB/file, 500 MB/patient soft warning).
- **Backup integration is mandatory:** the container includes the attachment tree with per-file
  SHA-256 in the manifest, so a database-only backup cannot silently occur. Missing files are reported
  at backup time as findings rather than ignored.
- Viewing: images and text render in-app; PDFs and unknown types open through the OS default handler
  with an explicit confirmation (never executed, never auto-loaded).

---

## 8. Read models for performance

`data/queries/` holds read-only projections used by lists, dashboards and reports:
`patient_list_view`, `appointment_day_view`, `queue_view`, `visit_history_view`,
`prescription_history_view`, `invoice_list_view`, `payment_day_view`, `receivable_view`,
`inventory_alert_view`, `dashboard_counters` (cached), `finance_period_view`.
Each is a single indexed SQL statement (or a small set) with no N+1 behaviour, covered by
`tests/perf/` timing budgets.

---

## 9. Testing of the data layer

`tests/integration/` covers, per repository: happy path, unique-constraint violation, FK violation,
nullable/optional handling, soft delete visibility rules, pagination boundaries, concurrent code
allocation (threaded), transaction rollback on injected failure, audit row emission, snapshot capture,
and schema migration from an empty file plus an older fixture DB. `tests/perf/` seeds a 50 000-patient
clinic with visits/prescriptions/invoices/payments and asserts the query budgets listed in
`00-architecture-overview.md §9`.
