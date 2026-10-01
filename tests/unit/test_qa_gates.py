"""The static quality gates are part of the release contract, so they are tested like product code.

These tests pin the behaviour that matters: the waiver pragma is parsed correctly, the rules detect
what they claim to detect, the money representation cannot be quietly weakened, and every gate passes
on the current tree in development mode.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
QA_DIR = REPO_ROOT / "tools" / "qa"


@pytest.fixture(scope="module", autouse=True)
def _qa_importable() -> None:
    """Make the gate modules importable for the duration of this module."""
    sys.path.insert(0, str(QA_DIR))
    yield
    sys.path.remove(str(QA_DIR))


class TestWaiverPragma:
    def test_parses_rule_with_hyphen_and_reason(self) -> None:
        from _common import _rules_from

        assert _rules_from("x = 1  # qa-allow: debug-print - reason here") == {"debug-print"}

    def test_parses_multiple_rules(self) -> None:
        from _common import _rules_from

        assert _rules_from("x = 1  # qa-allow: debug-print, float-in-finance - two rules") == {
            "debug-print",
            "float-in-finance",
        }

    def test_parses_wildcard(self) -> None:
        from _common import _rules_from

        assert _rules_from("x = 1  # qa-allow: all") == {"all"}

    def test_no_pragma_means_no_rules(self) -> None:
        from _common import _rules_from

        assert _rules_from("x = 1  # ordinary comment") == set()

    def test_waived_checks_the_line_above(self) -> None:
        from _common import waived

        lines = ["y = 1  # qa-allow: debug-print", "x = 1"]
        assert waived(lines, 2, "debug-print")
        assert not waived(lines, 2, "float-in-finance")


class TestDetectionRules:
    def test_silent_broad_handlers_are_found(self) -> None:
        from check_no_placeholders import _silent_broad_handlers

        source = (
            "try:\n    pass\nexcept Exception:\n    pass\n"
            "try:\n    pass\nexcept OSError:\n    pass\n"
            "try:\n    pass\nexcept Exception:\n    log()\n"
        )
        lines = _silent_broad_handlers(ast.parse(source))
        assert lines == [3], "only the broad, silent handler is a defect"

    def test_forbidden_network_import_is_detected(self) -> None:
        from check_offline import FORBIDDEN_MODULES, _imported_modules

        modules = dict(
            _imported_modules(
                ast.parse("import requests\nfrom http.client import HTTPConnection\n")
            )
        )
        assert "requests" in modules
        assert "http.client" in modules
        assert {"requests", "http.client"} <= FORBIDDEN_MODULES

    def test_money_module_keeps_rejecting_floats(self) -> None:
        text = (REPO_ROOT / "src" / "dentivapro" / "core" / "money.py").read_text(encoding="utf-8")
        assert "from decimal import" in text
        assert "isinstance(value, float)" in text, "float input must never be accepted as an amount"


class TestGatesOnTheRepository:
    def test_every_gate_passes_in_development_mode(self) -> None:
        result = subprocess.run(
            [sys.executable, str(QA_DIR / "check_all.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"static gates failed:\n{result.stdout}\n{result.stderr}"

    def test_traceability_matrix_is_structurally_valid(self) -> None:
        from _common import Gate
        from check_traceability import _rows, check_rows

        gate = Gate(name="test", purpose="matrix structure", release=False)
        rows = _rows(
            (REPO_ROOT / "docs" / "requirements-traceability.md").read_text(encoding="utf-8")
        )
        assert len(rows) >= 100, "the matrix must cover the specification, not a sample of it"
        check_rows(gate, rows)
        assert not gate.findings, "\n".join(finding.render() for finding in gate.findings)

    def test_release_mode_reports_unfinished_work(self) -> None:
        """Release mode must not silently pass while the matrix is still open."""
        result = subprocess.run(
            [
                sys.executable,
                str(QA_DIR / "check_traceability.py"),
                "--release",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "matrix-open" in result.stdout or "matrix-test" in result.stdout
