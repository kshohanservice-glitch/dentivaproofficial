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
