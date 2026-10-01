# Dentiva Pro

**Premium dental clinic management for dental practices in Bangladesh — offline, secure, and fully local.**

Dentiva Pro is a commercial Windows desktop application for running a dental clinic end to end: patients and
longitudinal clinical history, appointments and queue, dental charting, treatment catalogues, premium
prescriptions and invoices with reliable printing/PDF, payments and receivables, inventory with expiry and
low-stock control, income/expense accounting, granular role-based access control, audit trail, and verified
backup/restore.

**Everything works without an internet connection.** There is no paid API, no cloud database, no online
authentication service, no AI service and no recurring subscription anywhere in the product. After
installation and one-time offline activation, the clinic can run for years on a single Windows PC.

- **Product:** Dentiva Pro
- **Creator:** Shohan Khan — helloiamshohan@gmail.com
- **Target platform:** Windows 10 (1809+) / Windows 11, x64
- **Product language:** professional English UI, full Bengali (Unicode) content support, currency BDT (৳)

---

## Status

| Phase | Scope | Status |
|---|---|---|
| 0 | Discovery, environment verification, end-to-end architecture plan | **Complete** — see `docs/` |
| 1 | Foundation, project structure, design system, Windows shell | Not started (awaiting *Continue*) |
| 2–12 | Database/security → release | Not started |

The architecture is documented and frozen before implementation, as required:

| Document | Contents |
|---|---|
| [`docs/architecture/00-architecture-overview.md`](docs/architecture/00-architecture-overview.md) | Stack decisions with justification, layer diagram, runtime topology, config, logging, performance, risks |
| [`docs/architecture/01-domain-and-data-model.md`](docs/architecture/01-domain-and-data-model.md) | Entities, keys, indexes, money model, identifier strategy, integrity/deletion rules, attachments |
| [`docs/architecture/02-security-and-rbac.md`](docs/architecture/02-security-and-rbac.md) | Threat model, Argon2id, sessions/auto-lock, RBAC catalogue and seeded roles, audit, activation design |
| [`docs/architecture/03-ui-and-design-system.md`](docs/architecture/03-ui-and-design-system.md) | Design tokens, components, shell, responsive/DPI rules, keyboard contract, UI defect checklist |
| [`docs/architecture/04-printing-and-documents.md`](docs/architecture/04-printing-and-documents.md) | Print engine, profiles, prescription/invoice/thermal templates, failure handling, test matrix |
| [`docs/architecture/05-backup-and-restore.md`](docs/architecture/05-backup-and-restore.md) | Backup container format, verification, atomic restore, scheduling, destructive-action protection |
| [`docs/architecture/06-testing-and-quality.md`](docs/architecture/06-testing-and-quality.md) | Test levels, CI quality gates, performance budgets, definition of done |
| [`docs/architecture/07-build-installer-ci-release.md`](docs/architecture/07-build-installer-ci-release.md) | Packaging, installer behaviour, GitHub Actions, signing, release strategy |
| [`docs/architecture/08-dependency-license-audit.md`](docs/architecture/08-dependency-license-audit.md) | Dependency inventory, licences, redistribution obligations, zero-cost verification |
| [`docs/requirements-traceability.md`](docs/requirements-traceability.md) | 120 requirement groups mapped to design, code, tests and phases |
| [`docs/acceptance-test-matrix.md`](docs/acceptance-test-matrix.md) | Formal acceptance tests AT-001…AT-171 |
| [`docs/phase-plan.md`](docs/phase-plan.md) | The 13 phases, deliverables and acceptance gates |
| [`docs/environment-and-limitations.md`](docs/environment-and-limitations.md) | What was empirically verified here and what must be verified on Windows |

---

## Technology summary

| Layer | Choice |
|---|---|
| Language / runtime | Python 3.12 (bundled) |
| UI | PySide6 (Qt 6) Widgets with an in-repo clinical design system |
| Database | SQLite (WAL) with an explicit schema, repository and unit-of-work layer |
| Money | `Decimal` in the domain, integer paisa in the database — never binary floats |
| Printing / PDF | Qt `QPrinter` / `QPrintPreviewWidget` / `QPdfWriter` (offline, 300 dpi) |
| Security | Argon2id password hashing, service-layer RBAC, append-only audit log, derived offline activation |
| Packaging | PyInstaller (onedir) + NSIS installer |
| CI/CD | GitHub Actions: Linux quality gates, Windows bundle/installer build and smoke tests |

## Repository layout (target)

```
src/dentivapro/   {core,data,domain,services,security,printing,backup,ui,assets}
tests/            {unit,integration,services,security,printing,ui,perf,acceptance,regression}
tools/            seeding, QA gates, icon generation, activation constant derivation
packaging/        PyInstaller spec, NSIS installer script, smoke tests
.github/workflows/  ci.yml, windows-release.yml
docs/             architecture, user guides, developer guide, phase reports, licences
dist/             released artifacts (fallback location per project instructions)
```

## Licensing

Application code: proprietary, all rights reserved (see [`LICENSE`](LICENSE)).
Third-party components are used under their own licences and are listed in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md); Qt/PySide6 are used under LGPL-3.0 with dynamic
linking, and the fonts (Inter, Noto Sans Bengali) under the SIL Open Font License 1.1.

## Build and test (developer)

Commands become available in Phase 1 when the project structure and build configuration are established:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q                      # full local suite
python tools/seed.py --patients 50000 --seed 42   # performance dataset
python -m dentivapro           # launch the application
```

The production Windows installer is built exclusively by the GitHub Actions release workflow — never
claimed from a local development build.
