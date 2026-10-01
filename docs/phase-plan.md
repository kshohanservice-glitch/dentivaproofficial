# Dentiva Pro — Phase Plan (13 phases)

Execution is strictly sequential. Each phase ends with a report in `docs/phase-reports/` and the agent
**stops and waits for the user to say "Continue"**. No phase begins because the previous one is "mostly
done"; a phase closes only when its acceptance criteria pass.

| Phase | Scope | Key deliverables | Acceptance gate |
|---|---|---|---|
| **0** | Discovery, environment inspection, end-to-end architecture plan | This documentation set: architecture, data model, security/RBAC, UI system, printing, backup/restore, testing, build/CI/release, licence audit, traceability matrix, acceptance matrix, phase plan, environment limitations | Plan complete, internally consistent, environment capabilities proven by probes; reported; waiting for Continue |
| **1** | Foundation: repo structure, build config, app shell, design system, routing, logging, error boundary, config, DB foundation (connection/schema framework), initial Windows packaging pipeline | `src/dentivapro/**` skeleton, tokens + components, header/sidebar/router, structured logging, error boundary, settings registry, sqlite bootstrap, PyInstaller spec, NSIS skeleton, CI workflows, first tests | Shell renders with goldens; app starts and opens an empty initialised DB; CI workflow pushed and its run status determined; lint/type/test gates green |
| **2** | Database, domain model, security, auth, RBAC, audit, activation | Full schema + migrations, repositories, Argon2id auth, sessions, auto-lock, RBAC with service+query enforcement, audit subsystem, activation with derived verification | Security suite green incl. permission matrix and secret scan; schema/FK/migration tests green; activation tests green; audit coverage test green |
| **3** | Clinic setup, dentists, staff, users, configuration | First-run wizard (transactional, resumable), clinic/dentist/designation/qualification/signature management, user & role management, core settings screens | Setup happy path + interruption + atomicity tests green; staff/user/role acceptance tests green |
| **4** | Patients, profile, timeline, attachments, dental chart, visits, treatments, referrals | Complete patient subsystem, profile workspace, timeline, attachment service + viewer, adult/pediatric odontogram, visit editor, treatment catalogue, referrals | Patient/visit/chart/attachment/referral acceptance tests green; 50 k dataset perf test green; Bengali data tests green |
| **5** | Appointments, queue, prescriptions, clinical printing | Appointment calendar/list + conflict rules, queue workflow, prescription editor (multi-medicine, structured findings), print subsystem (profiles, preview, A4/A5/thermal, PDF) | Appointment/queue/prescription acceptance green; printing matrix green with artifacts reviewed; Bengali print fidelity green |
| **6** | Invoicing, payments, financial history, inventory, accounting | Invoice editor + numbering, multi-payment ledger, payment reports, inventory ledger/batches/expiry/low-stock, expenses, income, finance reports, financial permission enforcement | Money-exactness, payment, inventory, accounting and financial-permission tests green; report accuracy tests green |
| **7** | Dashboard, global search, notifications, reports, polish | Operational dashboard with permission-aware widgets, advanced global search, notification centre, operational reports, shortcuts, list performance | Dashboard permission-leak tests green; search/notification acceptance green; performance budgets green |
| **8** | Backup, restore, data safety, settings, destructive protection | Backup container + verification + scheduling, restore with pre-restore safety, integrity tooling, comprehensive settings, destructive-action guards | Backup/restore acceptance suite green incl. all failure paths; settings and destructive-guard tests green |
| **9** | Full system integration, performance, accessibility, responsiveness, stress | Cross-module integration, realistic end-to-end clinic scenarios, stress datasets, DPI and viewport matrix, state coverage audit, fixes | E2E acceptance matrix green; budgets green under stress; UI defect checklist executed with fixes |
| **10** | Security, dependency, licence, code-quality and architecture audit | Deep audit + fixes: dead code, placeholders, secrets, authz bypass, path handling, SQL, transactions, races, memory, complexity; dependency/licence verification | Zero open critical findings; all audit fixes retested; gate scripts green |
| **11** | Full regression, release candidate, installer validation, clean-machine testing | RC from the phase-complete commit, full regression, real installer built by CI, clean-machine sequence incl. print/PDF/backup/restore/uninstall/reinstall | Every RC acceptance item passes with evidence; any failure blocks release and forces a fix + full re-run |
| **12** | Final release audit and GitHub Actions release | Requirement-by-requirement final audit, final UI/DB/security/licence/installer/print/backup/RBAC/perf inspections, CI production build, GitHub Release (or `dist/`), release notes, hand-off | All final gates pass; artifact published or placed in `dist/` with an honest explanation; **no PR merge by the agent** |

## Rules carried through every phase

- Never merge a PR; the repository owner decides.
- Never silently downgrade a requirement; document any limitation, implement the best valid alternative,
  and report it.
- Fix defects found in earlier phases immediately and add regression tests.
- Keep the traceability matrix updated in the same PR as the work.
- Re-verify (do not assume) the state of the repository when resuming after an interruption.
