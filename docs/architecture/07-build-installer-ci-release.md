# Dentiva Pro — Build, Installer, CI/CD and Release Architecture (Phase 0)

---

## 1. Versioning

- Single source of truth: `src/dentivapro/version.py` → `__version__ = "1.0.0"`, `BUILD_NUMBER`,
  `RELEASE_CHANNEL` (`stable`). The installer, About screen, diagnostics pack, bundle metadata and release
  tag all read from it; CI fails if the tag does not match.
- Product identity: **Dentiva Pro**, creator **Shohan Khan** (helloiamshohan@gmail.com), displayed in
  About and in the installer metadata.
- Version scheme: `MAJOR.MINOR.PATCH` (1.0.0 is the final release line for this product). Build metadata
  (`+CI<run_number>`) is included in the About screen's diagnostics view only.

## 2. Repository structure

```
dentivaproofficial/
├── src/dentivapro/
│   ├── core/            config, paths, logging, errors, money, ids, time, workers, i18n, version
│   ├── data/            db (connection, tx, migrations, schema/*.sql), repos/*, queries/*
│   ├── domain/          enums, dataclasses/value objects, validators, permission catalogue
│   ├── services/        business logic per aggregate (rbac-enforcing, transactional, audited)
│   ├── security/        auth, sessions, rbac, audit, activation
│   ├── printing/        profiles, models, renderers, templates, print_service, pdf
│   ├── backup/          container, writer, verifier, restore, scheduler, integrity
│   ├── ui/              shell, screens, components, design (tokens/stylesheet/fonts/svg), wizards
│   └── assets/          fonts, icons, notices (licences), logo, templates
├── tests/               unit, integration, services, security, printing, ui, perf, acceptance, regression
├── tools/               seed, qa gates, icon generation, activation constants, bundle checks
├── packaging/           PyInstaller spec, NSIS script, installer assets, smoke tests
├── .github/workflows/   ci.yml (linux fast gates), windows-release.yml (build + installer + release)
├── docs/                architecture, phase reports, traceability, acceptance matrix, licenses
├── dist/                released artifacts when GitHub Release is unavailable (per instruction)
└── pyproject.toml, README.md, CHANGELOG.md, LICENSE, THIRD_PARTY_NOTICES.md, .gitignore, .gitattributes
```

No monolith: each module has one responsibility, services are split per aggregate, screens are split per
module with their own sub-package when large.

## 3. Build pipeline

```
1. Static gates (lint, format, types, custom QA scripts)                  [ubuntu]
2. Test suite (unit/integration/services/security/printing/perf)          [ubuntu]
3. UI goldens + layout invariants (Linux baseline)                        [ubuntu]
4. Windows: UI goldens (authoritative), PyInstaller onedir bundle         [windows]
5. Windows: packaged-bundle smoke test (offscreen launch, DB init,
   prescription PDF render, reopen existing DB, asset/font presence,
   absence of dev files and sample data)
6. Windows: NSIS installer compile (per-user default, optional all-users)
7. Windows: installer smoke test (silent install → launch → verify data
   init → uninstall → verify cleanup policy)
8. Windows: sign if a certificate secret is present (signtool), else record
   "unsigned" honestly in the release notes and report
9. Upload artifacts (installer, portable zip, checksums, SBOM/notices)
10. Publish GitHub Release on tag  OR  write artifacts to dist/ fallback
```

## 4. Packaging details

- **PyInstaller onedir** (`packaging/dentivapro.spec`): includes Qt runtime, platform plugins
  (`platforms/qwindows.dll`, styles, imageformats), PySide6 essentials, argon2/cryptography extensions,
  fonts (Inter, Noto Sans Bengali), icons, licence notices, and the schema SQL files. Excludes: tests,
  dev tooling, `tkinter`, docs sources, sample data, `.db` files, `.pyc` for excluded modules, and any
  development server.
  Rationale for onedir over onefile: faster start (no self-extraction), DLLs remain replaceable files
  (LGPL compliance), and the installer can patch/verify individual files. A single-file installer is
  produced by NSIS on top of the onedir payload.
- **NSIS 3 installer** (`packaging/installer.nsi`):
  - Per-user install by default to `%LOCALAPPDATA%\Programs\DentivaPro` (no admin prompt); an all-users
    option installs to `%ProgramFiles%\DentivaPro` with elevation.
  - Creates Start Menu shortcut, optional Desktop shortcut, optional "Launch Dentiva Pro" on finish.
  - Registers the product in Add/Remove Programs with name, version, publisher (Shohan Khan), icon and
    estimated size; supports `/S` silent install and `/D=` custom directory.
  - Creates the data folder with an ACL allowing the installing user modify rights; never overwrites user
    data on upgrade; uninstall leaves data by default and offers a checkbox "Also remove all clinic data
    (irreversible)" that is unchecked by default and requires explicit confirmation.
  - Uninstall removes the install directory, shortcuts and registry entries cleanly; refuses to remove the
    data folder when it is in use; writes an uninstall log to `%TEMP%`.
  - Every installer string is translatable and UTF-8 capable (Bengali clinic names in paths are supported;
    the app's data root default is ASCII to avoid legacy path issues).
- **Code signing:** if `WINDOWS_CERT_PFX`/`WINDOWS_CERT_PASSWORD` secrets exist, CI signs the EXE and the
  installer with `signtool` (SHA-256 + timestamp) and verifies the signature. If not present, the release is
  explicitly documented as **unsigned** (SmartScreen will warn on first run) — no fabricated claim.
- **Reproducibility:** pinned dependency versions (`requirements.lock` with hashes), pinned Qt version,
  deterministic ordering in PyInstaller inputs, and a recorded `SHA256SUMS` file.

## 5. GitHub Actions workflows

**`.github/workflows/ci.yml`** — triggers: push to any branch, pull requests, manual dispatch.
Jobs: `linux-quality` (lint/types/tests/coverage/printing matrix/perf), `linux-ui` (UI goldens),
`windows-build` (bundle + smoke + installer + installer smoke, artifact upload), `security` (permission
matrix, secret scan, dependency/licence audit report as an artifact). Concurrency cancel-in-progress;
`fail-fast: false` so all gates report.

**`.github/workflows/windows-release.yml`** — triggers: tag `v*` or manual dispatch with version input.
Runs the full gate set, builds the installer, signs when secrets exist, generates `SHA256SUMS`, uploads
artifacts, and publishes a GitHub Release with the installer, portable zip, checksums, notices and release
notes when `permissions: contents: write` is available. If release publication is unavailable, the job
writes the artifacts into `dist/` in the repository and the report states exactly why.

**Verification policy for this project:** the release artifact must come from CI. In this sandbox the
GitHub token may lack the `actions` scope (a probe returned HTTP 403 for the Actions API), so the ability
to trigger and read runs will be verified in Phase 1 and reported honestly. If runs cannot be triggered or
observed, the release report will state: artifacts were built by the CI workflow definition, the local
build was used for verification, and publishing requires the user's repo-level Actions permissions.
There is no silent substitution of a local build for a CI release.

## 6. Release strategy

- Branching: `main` (protected conceptually: users merge PRs manually), feature branches
  `arena/*` or `phase/*`, PR per phase with a report. **The agent never merges a PR.**
- Tag on release: `v1.0.0`, annotated, pointing at the RC-validated commit.
- Release contents: `DentivaPro-Setup-1.0.0.exe` (installer), `DentivaPro-1.0.0-portable.zip`,
  `SHA256SUMS.txt`, `THIRD_PARTY_NOTICES.md`, `RELEASE_NOTES.md`, plus the CI evidence summary.
- Fallback: `dist/` in the repository holds the same artifacts with a `dist/README.md` explaining the
  build run, commit and checksums.
- Rollback plan: because this is a single-machine offline product, rollback = reinstall the previous
  installer; data compatibility is guaranteed by the schema-version guard and pre-migration backups.

## 7. Environment limitations affecting release (documented)

- No Windows machine is available to this sandbox; the installer can only be produced and smoke-tested in
  GitHub Actions `windows-latest`. The sandbox can still produce and verify the *bundle contents* and all
  non-EXE artifacts (schema, templates, PDFs, tests, goldens).
- GitHub's release-asset CDN is blocked here, so dependencies are fetched from the npm/PyPI registries
  (verified reachable) and Linux-side wheels/tools are limited to those registries.
- If CI cannot run for the user's account, `dist/` will hold the artifacts produced by the workflow's
  documented equivalent plus a precise statement of what remains to be executed in CI.

## 8. Operational documentation shipped with the product

`docs/user/` contains: `installation.md`, `first-run-setup.md`, `daily-workflow.md`,
`printing-guide.md`, `backup-restore-guide.md`, `security-and-roles.md`, `troubleshooting.md`,
`faq.md`. `docs/development.md` covers building, testing, seeding, regenerating goldens and releasing.
Both sets are written as deliverable documentation, not as internal notes, and are reviewed in Phase 12.
