# Static quality gates

These scripts enforce rules that a normal test suite cannot express: they inspect the *source tree*
rather than the running program. They are plain Python (no third-party imports) so they run in CI
before the test dependencies are installed, and they are covered by `tests/unit/test_qa_gates.py`.

| Gate | Enforces |
|---|---|
| `check_no_placeholders.py` | No `TODO`/`FIXME`/`XXX`/`HACK`, no `print()` outside the diagnostic CLI, no silently swallowed broad exceptions, no hex colours outside `ui/design/`. In `--release` mode also: no placeholder wording and no development scaffolding (the "not implemented yet" screen must be gone and no navigation entry may still be unimplemented). |
| `check_money.py` | Accounting values are never binary floats: no `float()` in the money/data/service layers, no `REAL`/`FLOAT`/`DOUBLE`/`NUMERIC` columns, `*_paisa`/`*_minor` columns are `INTEGER`, and `core/money.py` keeps using `Decimal` and rejecting float input. |
| `check_offline.py` | No HTTP/socket client library is imported by product code (`socket` is accepted for the local host name only), no outbound URL call, and no runtime dependency that implies an online service. |
| `check_traceability.py` | The requirement matrix is well formed (sequential ids, all columns present, valid status and phase). In `--release` mode: no open row, and every referenced `tests/...` path exists. |

Run everything:

```bash
python tools/qa/check_all.py             # development mode — what CI enforces on every push
python tools/qa/check_all.py --release   # release mode — part of the release gate
```

## Waiving a finding

A finding may be waived **at the code site** with a reason, so the exception is visible in review:

```python
value = float(raw)  # qa-allow: float-in-finance - converting a legacy CSV value at the import edge
```

The pragma applies to the line it is on and to the line below it. A bare waiver without a reason still
passes, but reviewers are expected to ask for one; the release audit checks them.

## Why these gates exist

The product specification forbids demo content, placeholders, dead buttons, hard-coded prices, network
dependencies and float money. Those rules are easy to state and easy to break silently during a
long build. Each rule above is therefore checked mechanically on every push, and the release mode makes
the difference between "under construction" and "shippable" explicit rather than a matter of opinion.
