# Dentiva Pro — Security, Authentication, RBAC, Audit and Activation (Phase 0)

---

## 1. Threat model (offline desktop application)

| # | Threat | Realistic? | Control |
|---|---|---|---|
| T1 | Unauthorised person at the clinic PC opens the app and reads patient/financial data | Yes — the key threat | Login required, no stored session password, auto-lock (5/10/15/30 min), full-window lock layer, session invalidated on lock, audit of sessions |
| T2 | Staff member with limited role reaches restricted data (financial reports, accounting, other users' data) | Yes | Permission checks in the **service layer** for every sensitive operation, verified by an automated bypass test suite; UI merely reflects the decision |
| T3 | Password/secret theft from the database file | Yes (USB copy of `dentivapro.db`) | Argon2id (m=64 MiB, t=3, p=2, 16-byte salt, 32-byte tag); no plaintext or reversible storage anywhere; activation code never stored |
| T4 | Brute-force / credential stuffing at the login screen | Yes | Failure counting, exponential back-off, temporary lock-out, per-attempt audit, constant-time verification, uniform error messages |
| T5 | Tampering with the activation state to bypass activation | Moderate | Activation verifier is derived (never the code), obfuscated and split; state file is HMAC-protected; tampering is detected and reported as a re-activation requirement, never as data loss |
| T6 | Recovering the activation code from the shipped artifact | Possible with enough reverse-engineering effort — **acknowledged limitation** | No plaintext anywhere in source/config/logs/docs/bundles; derived + obfuscated verifier; high KDF cost per guess; verification code lives only in build-time tooling. **We do not claim mathematical secrecy for an offline fixed secret.** See §7 |
| T7 | Malicious/incorrect attachment filename or path | Yes | UUID storage names, extension allow-list, resolved-path containment check, size limits, no execution of stored files |
| T8 | SQL injection through search/filters | Moderate | 100 % parameterised SQL (enforced by a CI grep gate + review); search normalisation in Python, never string-concatenated SQL |
| T9 | Audit trail tampering by an ordinary user | Yes | Append-only triggers block UPDATE/DELETE on `audit_log`; UI has no edit path; audit writes happen inside the same transaction as the business change |
| T10 | Data theft of the backup file | Yes (USB / email) | Optional passphrase-protected backups (scrypt + AES-256-GCM); documented recommendation; never required for normal use |
| T11 | Denial of service by corrupting or locking the DB | Moderate | WAL + integrity checks, pre-migration backups, single-instance lock, clear recovery guidance, restore path |
| T12 | Privilege escalation through UI state manipulation | Yes | Permissions are re-evaluated on every service call from the server-side session object; disabling widgets is cosmetic only |
| T13 | Log leakage of sensitive content | Moderate | Redaction filters; explicit rule set for what may be logged (ids, actions, codes) vs never (passwords, medical free text, activation attempts) |
| T14 | Another local Windows user reads the data root directly | Yes | Documented: an offline desktop app cannot defend against an OS-level administrator; mitigate with Windows ACLs from the installer, optional backup encryption, and a Settings option to move the data root to a protected/BitLocker volume |

---

## 2. Password storage

- Algorithm: **Argon2id**, `time_cost=3`, `memory_cost=65536 KiB (64 MiB)`, `parallelism=2`,
  `salt_len=16`, `hash_len=32` (measured ≈ 76 ms on the target class of hardware).
  Parameters are stored in the hash string, so they can be raised later without breaking old users
  (a stronger-cost rehash happens transparently on the next successful login).
- Validation policy (enforced at the service layer, shown live in the UI): minimum 10 characters,
  must contain letters and digits, must not be a common/weak password (bundled list of ~10 000 entries,
  stored hashed for lookup), must not equal the username or clinic name, maximum 128 characters (DoS guard),
  Unicode allowed (Bengali passwords work).
- Password change, admin reset (forces change at next login), and account deactivation are audited.
- Passwords never appear in logs, error messages, diagnostics packs or the UI (masked fields, no
  "show password" in admin reset flows, clipboard cleared after a generated-password copy).
- Verification uses `argon2.verify` (constant-time comparison internally). Unknown usernames still
  perform a dummy Argon2 verification so response timing does not reveal account existence.

---

## 3. Sessions, locking and login controls

| Control | Design |
|---|---|
| Session creation | On successful login a `session` row is created (uuid, user, start, app version, machine label); the in-memory `SessionContext` holds user, role, granted permission set, session id |
| Auto-lock | Configurable idle timeout: **5, 10, 15, 30 minutes** (default 15). A single QTimer tracks user activity across the whole app (mouse, keyboard, touch); on expiry the lock layer covers the window, masks sensitive values, stops background UI timers, and marks `session.locked_at`. Setting `Never` is *not* offered |
| Unlock | Requires the locked user's password (Argon2 verified, throttled). An administrator may unlock with their own credentials, which is audited as `session.unlock_by_admin` and recorded in the notification centre |
| Lockout | 5 consecutive failures → 15-minute lock (configurable 5–60), exponential delay from the 3rd attempt, unlocking audited; administrators can clear a lock with explicit confirmation |
| Logout | Ends the session (`ended_at`, `end_reason='logout'`), clears the in-memory context, returns to the login screen; the lock layer is destroyed |
| Invalidation | Any permission/role change or deactivation immediately invalidates the target user's permission cache; an active session of a deactivated user is terminated at the next interaction |
| Inactivity on first-run | The setup wizard runs in a pre-session state; auto-lock applies as soon as the admin account exists |

---

## 4. RBAC architecture

### 4.1 Enforcement chain

```
UI action ──▶ service method:
              1. resolve SessionContext (must exist and be unlocked)
              2. require(permission_code)  ← raises PermissionDenied, writes audit 'security.permission_denied'
              3. validate input (domain validators)
              4. open transaction → repository writes → audit writes → commit
Repository layer additionally re-checks "deny-by-default" guard for sensitive tables
(see 4.4), so a coding error in a service cannot silently expose finance data.
```
- Permissions are resolved from role grants + per-user overrides at login and cached in the session;
  the cache is invalidated on any change to roles, grants, overrides, user status or password.
- A missing session, a locked session, or an unknown permission code is **denied**, never allowed.
- `PermissionDenied` is a domain error: the UI shows a professional "You do not have permission"
  state, and the event is audited (`severity=warning`).

### 4.2 Permission catalogue (canonical codes)

**Practice**
`dashboard.view`, `patient.view`, `patient.create`, `patient.edit`, `patient.archive`,
`patient.delete_permanent` (admin, typed confirmation), `patient.export`, `patient.print`,
`patient.attachment.view`, `patient.attachment.add`, `patient.attachment.delete`,
`appointment.view`, `appointment.create`, `appointment.edit`, `appointment.cancel`,
`appointment.manage_settings`, `queue.view`, `queue.manage`

**Clinical**
`visit.view`, `visit.create`, `visit.edit`, `visit.void`, `dental_chart.view`, `dental_chart.edit`,
`treatment.catalog.view`, `treatment.catalog.manage`, `prescription.view`, `prescription.create`,
`prescription.edit`, `prescription.finalize`, `prescription.void`, `prescription.print`,
`prescription.manage_settings`, `referral.view`, `referral.create`, `referral.edit`,
`clinical_catalog.manage` (finding/tooth-condition catalogues), `medicine_catalog.manage`

**Billing & finance**
`invoice.view`, `invoice.create`, `invoice.edit_draft`, `invoice.finalize`, `invoice.void`,
`invoice.print`, `payment.view`, `payment.create`, `payment.void`, `finance.report.view`,
`finance.accounting.view`, `finance.expense.view`, `finance.expense.create`, `finance.expense.void`,
`finance.income.view`, `finance.income.create`, `patient.financial.view` (outstanding/ledger),
`finance.export`, `finance.settings.manage`

**Inventory**
`inventory.view`, `inventory.manage`, `inventory.purchase`, `inventory.adjust`, `inventory.report.view`,
`inventory.cost.view` (costs are financially sensitive), `inventory.settings.manage`

**Administration**
`staff.view`, `staff.manage`, `user.view`, `user.manage`, `role.manage`, `permission.manage`,
`settings.view`, `settings.manage`, `print.profile.manage`, `backup.view`, `backup.create`,
`backup.restore`, `backup.settings.manage`, `data.export`, `data.destructive`
(delete all data / reset application / delete clinic — always typed-confirmation), `audit.view`,
`audit.export`, `diagnostics.export`, `notification.view`, `notification.manage`, `about.view`

Sensitive (`permission.is_sensitive=1`): everything under Billing & finance restrictions,
`inventory.cost.view`, `audit.*`, `user.*`, `role.*`, `permission.*`, `settings.manage`,
`backup.restore`, `data.destructive`, `patient.delete_permanent`.

### 4.3 Seeded roles (all editable; overrides per user are allowed)

| Permission area | Administrator | Dentist | Receptionist | Billing Officer | Assistant | Inventory Manager | Auditor |
|---|---|---|---|---|---|---|---|
| Dashboard | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Patients view | ✔ | ✔ | ✔ | ✔ | ✔ | — | ✔ |
| Patients create/edit | ✔ | ✔ | ✔ | — | ✔ | — | — |
| Patient archive/permanent delete | ✔ | — | — | — | — | — | — |
| Attachments | ✔ | ✔ | ✔ (add/view) | — | ✔ | — | ✔ (view) |
| Appointments / Queue | ✔ | ✔ | ✔ | — | ✔ (queue) | — | ✔ (view) |
| Visits / dental chart | ✔ | ✔ | — | — | ✔ (view/edit) | — | ✔ (view) |
| Treatment catalog | ✔ | ✔ | — | — | — | — | ✔ (view) |
| Prescriptions | ✔ | ✔ | — | — | ✔ (create/edit) | — | ✔ (view) |
| Referrals | ✔ | ✔ | ✔ | — | ✔ | — | ✔ |
| Invoices (operational) | ✔ | ✔ (view/create) | ✔ | ✔ | — | — | ✔ (view) |
| Payments (receive money) | ✔ | — | ✔ | ✔ | — | — | ✔ (view) |
| Financial reports / accounting | ✔ | — | — | ✔ (reports) | — | — | ✔ (view) |
| `patient.financial.view` (balances) | ✔ | — | ✔ (outstanding only) | ✔ | — | — | ✔ |
| Expenses | ✔ | — | — | ✔ | — | ✔ (supplies only) | ✔ (view) |
| Inventory | ✔ | — | — | — | ✔ (use stock) | ✔ | ✔ (view) |
| Inventory costs | ✔ | — | — | ✔ | — | ✔ | ✔ |
| Staff & Users | ✔ | — | — | — | — | — | ✔ (view) |
| Roles & permissions | ✔ | — | — | — | — | — | — |
| Settings (operational) | ✔ | ✔ (clinical/print) | — | — | — | ✔ (inventory) | — |
| Backup / Restore | ✔ | — | — | — | — | — | — (view only) |
| Destructive data actions | ✔ | — | — | — | — | — | — |
| Audit log | ✔ | — | — | — | — | — | ✔ |

The table is the *seed*; the administrator can change every cell in Settings → Roles, and the
permission model supports per-user overrides for real clinics with irregular staffing.

### 4.4 Deny-by-default guard for sensitive queries

`data/repos/_guard.py` provides `require_finance_read(session)` / `require_admin(session)` helpers that
the financial read models (`receivable_view`, `payment_day_view`, `finance_period_view`,
`inventory_cost_view`) call before executing. This is a second line of defence behind the service
checks; a unit test enumerates every exported function in `data/queries/` and asserts that each either
declares itself public or calls a guard.

### 4.5 Verifying that hiding is not security

`tests/security/test_permission_matrix.py` drives a **table of (service, method, required permission)**
and asserts that, for a caller lacking the permission:
1. the service raises `PermissionDenied` before any SQL statement executes (verified with a statement
   spy on the connection),
2. no row is inserted/updated/deleted (verified by row counts before/after),
3. an audit record with `security.permission_denied` is written,
4. the corresponding read model raises instead of returning `[]` where emptiness would itself be a leak
   (e.g. a payments list must deny, not silently show nothing).
The same suite runs for every seeded role, so its correctness scales if a permission is later changed.

---

## 5. Audit trail

**Actions audited (mandatory):** authentication (login success/failure/logout/lock/unlock/admin unlock/
lockout/password change/reset), user/role/permission changes, settings changes (before/after),
first-run setup steps and completion, patient create/edit/archive/permanent delete, attachment
add/delete, visit create/edit/void, prescription finalise/void/reprint, invoice finalise/void/print,
payment post/void, expense post/void, inventory adjustments and write-offs, backup created/failed/
restored, restore started/pre-restore backup/restore verified/restore failed, destructive actions,
integrity checks and their fixes, activation success/failure/suspicious state, permission denials.

**Record shape:** `at_utc`, actor (id + username snapshot), session id, action code, entity
(type/id/business code), human summary, `before_json`/`after_json` (redacted field-level diff where
practical), severity, machine label, app version, correlation id.

**Immutability:** `BEFORE UPDATE`/`BEFORE DELETE` triggers on `audit_log` raise `ABORT`. The UI exposes
read + filtered export only (permission `audit.view`/`audit.export`). Rotation/compaction is not
implemented because the DB is local; Settings → Data shows the size and offers an audited archive
export + truncation of records older than a chosen date, which itself is audited.

**Coverage test:** `tests/acceptance/test_audit_coverage.py` performs each audited action and asserts the
expected action code appears with the right actor/entity.

---

## 6. File-system security

- Data root and backup folders are validated (exists, writable, not a system folder, not inside the
  install directory, sufficient free space) before any operation that could write.
- Attachment names/extension allow-list; UUID storage names; resolved-path containment check.
- Importing a backup validates every entry path against the target root (zip-slip protection),
  rejects absolute paths, `..` segments, symlinks and oversized entries before extraction.
- Exports are written to the configured export folder with sanitised, deterministic names.
- Temporary files use `.partial` suffixes and are cleaned on startup if a previous run was interrupted.

---

## 7. Activation design (fixed offline secret)

**Mandated code:** provided privately for the build. It must never appear in plaintext in source,
configuration, frontend bundles, logs, comments, shipped documentation or easily searchable resources.

**Design**

```
build time (tools/derive_activation_constants.py, run by the release engineer, not shipped):
  salt      = SHA-256(b"dentivapro.activation.v1" || BUILD_SALT_16_BYTES)
  verifier  = PBKDF2-HMAC-SHA256(normalised_code, salt, iterations = 800_000, dklen = 32)
  fragments = obfuscate(verifier)  → 4 fragments XOR-masked with per-fragment masks,
              published as disguised byte arrays across two modules

runtime (security/activation.py):
  normalise input (strip spaces/dashes, upper-case, digits only)
  candidate = PBKDF2-HMAC-SHA256(normalised, salt, 800_000, 32)
  compare   = hmac.compare_digest(candidate, deobfuscate(fragments))
  on success → create protected activation state; on failure → uniform message + attempt audit + delay
```

- **State:** `<data root>/activation.dat` stores `{installation_id, activated_at, app_version,
  machine_fingerprint, verifier_fingerprint}` signed with HMAC-SHA-256 keyed by
  `HKDF(build_secret, machine_fingerprint)`. The DB mirrors non-secret fields in `app_meta` for audit and
  restore detection. Corruption or tampering ⇒ the app asks for activation again; data is untouched.
- **Restore to another machine:** the state no longer validates. The app explains that the backup came
  from another installation and asks for the activation code again (it does not delete or alter data).
- **Anti-automation:** a minimum 1-second gap between attempts, an attempt counter in the state file, and
  audit records for every attempt; no lockout that could strand a legitimate clinic.
- **Robustness:** valid activation survives restarts, application updates within 1.x, moving the data
  root (the state file travels with the data root and re-binds to the machine on first start).
- **Honest limitation (documented in `docs/environment-and-limitations.md` and the release report):**
  because verification is local, a determined attacker who controls the machine can recover the
  verifier and patch the check. The controls above raise the cost substantially and eliminate plaintext
  exposure and casual extraction; they do not provide mathematical secrecy.
- **Test strategy:** activation tests use dependency injection (`ActivationService(verifier=…)`) with a
  synthetic secret, so the real derived constants never appear in tests, fixtures or CI logs.
  `tools/verify_no_secrets.py` scans the built bundle, source tree, docs and logs for the literal code
  and its derived constants in multiple encodings (ASCII, UTF-16, base64, hex, reversed) and fails CI
  if found. The literal code is provided to CI only as an encrypted repository secret used by the
  release job's scan step (never echoed).

---

## 8. Security testing summary

`tests/security/` covers: password hashing (algorithm parameters, rehash path, weak-password rejection),
lockout/back-off, timing uniformity for unknown users, session invalidation on permission change,
permission-denial matrix across all seeded roles (service-level + read-model guards), audit immutability
(SQL attempt to update/delete), attachment path-traversal and extension allow-list, zip-slip during
restore, activation derivation with synthetic verifier, activation-state tampering, secret scan of
`dist/` artifacts, and a grep gate for parameterised SQL and bare `except: pass`.
