# Changelog

All notable changes to Dentiva Pro are documented here. This project follows a strict phase workflow;
each phase ends with a report in `docs/phase-reports/`.

## [Unreleased] — 1.0.0 development

### Added — Phase 0: Discovery, environment verification and architecture plan
- Complete architecture documentation set (9 documents) covering stack decisions and justification,
  data model, security/RBAC/audit/activation, design system, printing, backup/restore, testing,
  build/installer/CI/release and dependency/licence audit.
- Requirements traceability matrix: 120 requirement groups mapped to design sections, implementation
  modules, verification methods and phases.
- Formal acceptance test matrix: AT-001…AT-171, split into automated, performance-budgeted and
  manual clean-machine items.
- 13-phase execution plan with explicit acceptance gates per phase.
- Environment capability report recording what was empirically verified (Qt headless rendering, Bengali
  shaping, offline PDF, SQLite performance at 100 k rows, Argon2id cost, Windows wheel availability) and
  what cannot be verified in this environment (Windows EXE execution, physical printers, code signing).
- Repository scaffolding: `.gitignore`, `.gitattributes`, `LICENSE` (proprietary), `README.md`.

Nothing else has been implemented yet. No production code, no schema and no build configuration exist at
this point by design: implementation starts in Phase 1 after explicit approval.

### Added — Phase 1: Foundation, design system and Windows shell
- Build configuration (`pyproject.toml`): src layout, pinned runtime and development dependencies,
  strict mypy, ruff, pytest and coverage settings.
- Design system: design tokens (light palette, typography, spacing, radii, elevation, motion, metrics,
  responsive breakpoints), a single stylesheet keyed by `objectName`/`variant`/`state`, bundled
  Inter + Noto Sans Bengali fonts (SIL OFL-1.1) with Bengali detection, and a 62-icon Lucide SVG subset.
- Application shell: collapsible sidebar with the Practice/Clinical/Billing/Administration areas and all
  mandated destinations, header with product/clinic identity, live date, session and help menus, router
  with history and permission-denial reporting, keyboard shortcuts and a shortcut reference dialog,
  toasts, status bar and an honest "foundation build" banner.
- Components and screens: cards, banners, state panels (empty/loading/error/permission-denied/development),
  data table with a virtualised model, About screen (identity, creator, diagnostics, bundled notices) and
  explicit pending-module screens for modules delivered in later phases.
- Core services: typed error hierarchy, path resolution with a documented order, structured JSONL logging
  with privacy redaction, decimal-safe money (`Money` over `Decimal`, no binary floats for accounting),
  date/Bengali-digit utilities, configuration, ID/patient-code generation, i18n catalogue, worker
  framework and a typed settings registry.
- Data foundation: SQLite bootstrap (WAL, foreign keys, integrity checks), migration runner with version
  guarding and history, base schema (`001_base.sql`) and repositories for meta/sequence/settings.
- Quality automation: 302 tests, UI golden-image store with a documented promotion workflow, secret scan,
  Qt development-sandbox recipe and an icon-set generator.
- Packaging and CI: PyInstaller onedir spec, version-resource generator, bundle audit + offscreen launch
  smoke test, NSIS per-user installer skeleton with an explicit clinic-data choice on uninstall, and a
  GitHub Actions workflow (quality gates, Linux test suite, Windows bundle/installer validation).
- Phase report: `docs/phase-reports/phase-1-report.md` (including the two gate items that still require
  evidence from a Windows runner and from the repository owner's Actions visibility).
