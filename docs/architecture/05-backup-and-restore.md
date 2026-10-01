# Dentiva Pro — Backup, Restore and Data-Safety Architecture (Phase 1)

Backup is a commercial requirement: a clinic that loses patient and financial history has lost the
business. This subsystem is therefore verified, atomic, self-describing and never silently partial.

---

## 1. Backup container format — `.dprobackup`

A ZIP container (stdlib `zipfile`, `ZIP_DEFLATED`) with a strict, validated structure:

```
manifest.json                 metadata + integrity index
dentivapro.db                 consistent database snapshot (VACUUM INTO output)
attachments/<patient>/<uuid>.<ext>   every file referenced by attachment rows
licenses/NOTICE.txt           origin note (Dentiva Pro, version, machine label, creator info)
```

`manifest.json`:

```json
{
  "format": "dentivapro-backup",
  "format_version": 1,
  "app_version": "1.0.0",
  "schema_version": 7,
  "created_at_utc": "2026-10-01T09:15:22Z",
  "created_by_user": "admin",
  "machine_label": "CLINIC-PC",
  "installation_id": "…",
  "reason": "manual|scheduled|pre-restore|pre-migration",
  "counts": {"patients": 4123, "visits": 18244, "invoices": 9012, "payments": 10455,
             "prescriptions": 8801, "inventory_items": 284, "attachments": 612},
  "db": {"file": "dentivapro.db", "bytes": 91234567, "sha256": "…", "sqlite_user_version": 7},
  "attachments_index": [{"relpath": "attachments/12/uuid.jpg", "bytes": 321045, "sha256": "…"}],
  "integrity": {"db_integrity_check": "ok", "foreign_key_check": "ok", "missing_attachment_files": 0},
  "encryption": {"enabled": false, "cipher": null, "kdf": null}
}
```

Backups are named `DentivaPro-backup-YYYY-MM-DD_HHMMSS-<reason>.dprobackup` (local time, deterministic
and sortable) written to the chosen folder (native folder-selection dialog in Settings and on demand),
to a staging `.partial` file first, then atomically renamed on success.

## 2. What is included (and therefore what is never left behind)

| Included | Reason |
|---|---|
| Full database snapshot | Clinical + financial + security data |
| All attachment files referenced by rows | Requirement: DB-only backups are forbidden |
| Settings, roles, users, audit log | Restores must preserve security and traceability |
| Dental chart records, queue history, notifications | Part of the operational state |
| Manifest with hashes | Verification and selective diagnostics |

Excluded deliberately (documented in the UI): log files, temporary files, `.trash` items, exports, and the
activation secret (state is re-bound on the target machine; the code is never stored in a backup).

## 3. Creating a backup (failure-safe)

1. Validate target folder: exists, writable, is not the install directory, free space ≥ estimated size × 1.25.
2. Checkpoint WAL (`PRAGMA wal_checkpoint(TRUNCATE)`) and take a consistent snapshot with `VACUUM INTO`
   (never copies a live database file by hand).
3. Run `PRAGMA integrity_check` + `foreign_key_check` on the snapshot; abort on failure with a clear error.
4. Stream the DB and attachments into the ZIP while computing SHA-256 per entry; report progress
   (files, bytes, ETA) and allow cancellation — a cancelled backup leaves only a `.partial` file, never a
   file that looks complete.
5. Re-open the finished container and re-verify hashes + manifest consistency (self-check).
6. Atomically rename to the final name; write a `maintenance_run` row (`success` with bytes + checksum) and
   an audit entry. **A backup is reported successful only if steps 1–5 all passed.**
7. Apply retention (`keep_last_n` per schedule, minimum 3) — only files matching our deterministic naming
   pattern in the configured backup folder are ever considered, so user files are never deleted.

Errors are explicit and specific: destination not writable, insufficient space (with required vs available),
network/USB drive removed mid-run, file locked, checksum mismatch, DB integrity failure. Every failure is
logged, shown in the UI, and recorded as a `failed` `maintenance_run` row with the reason. Nothing is
reported successful when it is not.

## 4. Restore (validated, atomic, reversible)

```
1. Choose file(s) → Open each manifest, validate format/version, app_version compatibility,
   schema_version ≤ current, and container health (manifest parse, entry list, hashes sampled then fully
   verified for DB + all attachments).
2. Pre-restore safety backup of the CURRENT state:
   backups/DentivaPro-backup-<ts>-pre-restore.dprobackup  (mandatory; restore is blocked if this fails).
3. Stage restore into <data root>/restore-staging/:
   extract DB and attachments with zip-slip protection (no absolute paths, no "..", no symlinks),
   verify every hash and the DB integrity + foreign keys on the staged copy, and run a domain sanity pass
   (counts > 0 where required, admin user exists, schema readable by the app).
4. Commit (atomic swap): close all DB connections → move current DB/attachments to
   <data root>/.restore-rollback/<ts>/ → move staged files into place → verify the live DB opens,
   integrity_check passes and the app can read the admin user + clinic identity.
5. On any failure during 4: roll back from `.restore-rollback/<ts>` automatically and report failure with
   the original data intact and the pre-restore backup path shown.
6. Post-restore: invalidate sessions, force re-login, re-bind activation state to this machine (ask for the
   code only if the state cannot be re-bound), write audit + maintenance_run records, and show a summary
   (what was restored, counts, source backup, pre-restore backup location).
```

Multi-file restore (when the architecture permits it meaningfully): the user may select several backups;
the app lists them with dates/counts and offers **the latest as the primary restore**, with the others
usable for comparison/attachment recovery. The app never merges two databases record-by-record, because
merging would silently corrupt financial history — the documented safe option is restoring one complete
generation and, if needed, recovering individual attachments from another container. This limitation and
its rationale are stated in the UI and in the release report.

Version compatibility: a backup from a **newer** schema than the running app is refused with an explanation
(no downgrade risk). An older schema triggers the same pre-migration backup + migration path used by
normal startup, with the migration result verified before the app continues.

## 5. Scheduling

`backup_schedule` supports **every 7 / 15 / 30 days** (plus manual-only), a target folder, retention count,
and attachment inclusion (attachments cannot be excluded without an explicit admin confirmation and a
warning that the backup will be incomplete — recorded in the manifest as a finding). The app evaluates the
schedule at startup, after each successful backup and hourly; when due, it shows a non-blocking prompt
(*Back up now* / *Snooze 1 day* / *Open backup settings*) and, if the administrator enabled it, runs the
backup automatically with progress in the notification centre. Missed schedules are reported honestly
("last backup 23 days ago, schedule 7 days") with a red badge in the header notification centre.
The status is always visible: last run (success/failure), next due, folder, size, and history list.

## 6. Integrity tooling (Settings → Data, and after every restore)

- `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, page/freelist stats.
- Domain checks: invoice totals vs lines/adjustments; `balance = total − paid`; status consistency;
  inventory stock vs movements; batch remaining vs movements; orphan attachment rows/files;
  duplicate business codes; required snapshot columns non-null on finalised documents.
- Findings are listed with severity and affected entity, and each fix is an explicit, audited action
  (no silent auto-repair). `VACUUM`/`ANALYZE` maintenance is offered with progress and a pre-run backup.

## 7. Destructive-action protection (Settings → Data)

| Action | Guard |
|---|---|
| Delete all clinical & financial data (fresh start, keep clinic/users) | `data.destructive` permission + typed phrase `DELETE ALL DATA` + mandatory backup first (offered, and required unless the admin explicitly acknowledges) + audit |
| Delete business/clinic identity and re-run setup | `data.destructive` + typed phrase + pre-action backup required + audit |
| Full application reset (recovery to a clean installation) | `data.destructive` + typed phrase + pre-action backup required + admin password re-entry + audit + post-reset state explanation |
| Permanently delete a patient with no dependents | `patient.delete_permanent` + typed patient code + audit; refused whenever any dependent row exists |
| Purge soft-deleted attachments | `data.destructive` + confirmation + audit (files moved to trash first, then removed) |
| Void an invoice/payment/expense | Domain permission + reason required + audit; the original row is never deleted |

Every destructive screen states plainly what will happen, what will be kept, and that the action is
irreversible, before the confirmation control is enabled.

## 8. Tests (`tests/backup/`)

Happy path (create → verify → restore → data identical by row counts and sampled hashes) · attachments
included and restored byte-identically · missing attachment file detected at backup time · corrupt
container (truncated, bad hash, invalid manifest, wrong format version) refused with the live data
untouched · destination not writable / insufficient space / device removed mid-run · cancel mid-backup
leaves no complete-looking file · pre-restore backup created and restorable · interrupted commit rolls back
automatically · restore of a newer-schema backup refused · restore of an older-schema backup migrates
correctly · scheduled run recorded and next-due computed for 7/15/30 days · retention keeps the newest N and
never deletes non-app files · empty database backup/restore · 2 GB synthetic backup completes within the
performance budget with UI progress.
