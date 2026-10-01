"""Tests for the packaging bundle audit (``packaging/check_bundle.py``).

The audit is what stands between a broken bundle and a shipped installer, and its first CI run exposed a
false negative (substring expectations that never matched the real self-check output). These tests pin
the parsing and the contents rules.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

PACKAGING = Path(__file__).resolve().parents[2] / "packaging" / "check_bundle.py"

SELF_CHECK_OUTPUT = """product         : Dentiva Pro 1.0.0
data root       : C:/ProgramData/Dentiva Pro
database        : C:/ProgramData/Dentiva Pro/dentivapro.db
journal mode    : wal
schema version  : 1
sqlite version  : 3.45.1
foreign keys    : on
integrity check : ok
bundled fonts   : ok
tables          : 5
setup complete  : no
"""


@pytest.fixture(scope="module")
def check_bundle() -> Any:
    spec = importlib.util.spec_from_file_location("check_bundle_under_test", PACKAGING)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_bundle(root: Path, *, icons: int = 50) -> Path:
    package = root / "_internal" / "dentivapro"
    (package / "assets" / "fonts").mkdir(parents=True)
    (package / "assets" / "fonts" / "Inter.ttf").write_bytes(b"font")
    (package / "assets" / "fonts" / "NotoSansBengali.ttf").write_bytes(b"font")
    (package / "assets" / "branding").mkdir(parents=True)
    (package / "assets" / "branding" / "app_icon.ico").write_bytes(b"icon")
    (package / "assets" / "notices").mkdir(parents=True)
    icons_dir = package / "assets" / "icons"
    icons_dir.mkdir(parents=True)
    for index in range(icons):
        (icons_dir / f"icon-{index}.svg").write_text("<svg/>", encoding="utf-8")
    schema = package / "data" / "db" / "schema"
    schema.mkdir(parents=True)
    (schema / "001_base.sql").write_text("-- schema", encoding="utf-8")
    return root


def test_clean_bundle_passes(check_bundle: Any, tmp_path: Path) -> None:
    assert check_bundle.check_contents(_make_bundle(tmp_path)) == []


def test_incomplete_icon_set_is_reported(check_bundle: Any, tmp_path: Path) -> None:
    problems = check_bundle.check_contents(_make_bundle(tmp_path, icons=5))
    assert any("icon set" in problem for problem in problems)


def test_missing_font_is_reported(check_bundle: Any, tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path)
    (bundle / "_internal" / "dentivapro" / "assets" / "fonts" / "Inter.ttf").unlink()
    problems = check_bundle.check_contents(bundle)
    assert any("Inter.ttf" in problem for problem in problems)


def test_database_and_test_code_are_rejected(check_bundle: Any, tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path)
    (bundle / "_internal" / "dentivapro" / "app.db").write_bytes(b"")
    tests_dir = bundle / "_internal" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_thing.py").write_text("def test_x(): pass", encoding="utf-8")
    problems = check_bundle.check_contents(bundle)
    assert any("app.db" in problem for problem in problems)
    assert any("forbidden path" in problem for problem in problems)


def test_self_check_output_is_parsed_as_key_value_pairs(check_bundle: Any) -> None:
    reported = check_bundle.parse_self_check(SELF_CHECK_OUTPUT)
    assert reported["journal mode"] == "wal"
    assert reported["schema version"] == "1"
    assert reported["bundled fonts"] == "ok"
    assert set(check_bundle.EXPECTED_SELF_CHECK) <= set(reported)


def test_expected_self_check_matches_the_real_output_format(check_bundle: Any) -> None:
    reported = check_bundle.parse_self_check(SELF_CHECK_OUTPUT)
    for key, expected in check_bundle.EXPECTED_SELF_CHECK.items():
        assert reported.get(key) == expected, key


def test_a_broken_self_check_would_be_detected(check_bundle: Any) -> None:
    broken = SELF_CHECK_OUTPUT.replace("foreign keys    : on", "foreign keys    : off")
    reported = check_bundle.parse_self_check(broken)
    assert reported["foreign keys"] == "off"
    assert reported["foreign keys"] != check_bundle.EXPECTED_SELF_CHECK["foreign keys"]
