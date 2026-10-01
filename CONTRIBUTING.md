# Commit convention

`<phase>: <imperative summary>` — one logical unit per commit, no streams of micro-commits.

Examples:
  `phase0: add end-to-end architecture, traceability and acceptance plans`
  `phase1: scaffold project structure, design tokens and application shell`
  `phase2: implement schema, authentication, RBAC, audit and offline activation`

# Branch and pull-request workflow

- Work happens on the session branch (`arena/<session-id>`) or on phase branches merged into it via PRs
  that only the repository owner merges.
- The agent never merges a pull request, never force-pushes `main`, and never rewrites published history.
- Each phase ends with: implementation + tests + updated traceability matrix + a phase report committed to
  `docs/phase-reports/`, then a PR (or a push to the session branch when the user prefers) and a report in
  the conversation.
- Release tags are `vX.Y.Z` and are created only after the Phase 12 gates pass.

# Quality gates that must pass before a phase is declared complete

1. `ruff check` and `ruff format --check`
2. `mypy` on `src/`
3. `pytest` (unit, integration, services, security, printing, UI, perf, acceptance as applicable)
4. Custom gates in `tools/qa/`: no placeholders/TODOs, no bare `except: pass`, no raw SQL concatenation,
   no raw styling outside the design system, no secrets, licence check, traceability check
5. Windows job where applicable: UI goldens, bundle smoke test, installer build and installer smoke test
