"""Logging must be useful for diagnosis and must never leak secrets or clinical text."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pytest

from dentivapro.core.errors import (
    ConflictError,
    DentivaError,
    PermissionDenied,
    ValidationError,
    to_user_error,
)
from dentivapro.core.logging import (
    JsonLineFormatter,
    RedactionFilter,
    close_logging,
    configure_logging,
    diagnostics_snapshot,
    get_logger,
    log_event,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def fresh_logging(tmp_path: Path):
    """Reconfigure logging into a temporary directory for one test."""
    from dentivapro.core.logging import _reset_for_tests

    _reset_for_tests()
    log_path = configure_logging(tmp_path / "logs", level="DEBUG")
    yield log_path
    _reset_for_tests()


class TestRedaction:
    def test_sensitive_keys_are_redacted(self) -> None:
        record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", (), None)
        record.payload = {
            "username": "admin",
            "password": "hunter2",
            "activation_code": "1234",
            "session_token": "abc",
            "password_hash": "$argon2id$...",
            "attempts": 3,
        }
        assert RedactionFilter().filter(record) is True
        assert record.payload["password"] == "[redacted]"
        assert record.payload["activation_code"] == "[redacted]"
        assert record.payload["session_token"] == "[redacted]"
        assert record.payload["password_hash"] == "[redacted]"
        assert record.payload["username"] == "admin"
        assert record.payload["attempts"] == 3

    def test_clinical_free_text_is_omitted(self) -> None:
        record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", (), None)
        record.payload = {"patient_id": 12, "notes": "patient has severe pain in 36"}
        RedactionFilter().filter(record)
        assert record.payload["notes"] == "[clinical text omitted]"
        assert record.payload["patient_id"] == 12

    def test_nested_payloads_are_redacted(self) -> None:
        record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", (), None)
        record.payload = {"request": {"password": "x", "user": "admin"}}
        RedactionFilter().filter(record)
        assert record.payload["request"]["password"] == "[redacted]"
        assert record.payload["request"]["user"] == "admin"

    def test_free_text_messages_containing_secrets_are_replaced(self) -> None:
        record = logging.LogRecord(
            "t", logging.INFO, __file__, 1, "user password=secretvalue", (), None
        )
        RedactionFilter().filter(record)
        assert "secretvalue" not in str(record.msg)


class TestJsonFormat:
    def test_record_becomes_a_single_json_line(self) -> None:
        record = logging.LogRecord("dentivapro.test", logging.INFO, __file__, 12, "hello", (), None)
        record.event = "test.event"
        record.payload = {"answer": 42}
        formatted = JsonLineFormatter().format(record)
        assert "\n" not in formatted
        payload = json.loads(formatted)
        assert payload["event"] == "test.event"
        assert payload["data"] == {"answer": 42}
        assert payload["level"] == "INFO"
        assert payload["logger"] == "dentivapro.test"

    def test_exceptions_are_included_for_diagnosis(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                "dentivapro.test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info()
            )
        payload = json.loads(JsonLineFormatter().format(record))
        assert "ValueError: boom" in payload["exc"]


class TestFileLogging:
    def test_events_are_written_to_the_log_file(self, fresh_logging: Path) -> None:
        logger = get_logger("dentivapro.tests")
        log_event(logger, logging.INFO, "unit.test_event", patient_id=7, amount=1250)
        for handler in logging.getLogger().handlers:
            handler.flush()
        content = fresh_logging.read_text(encoding="utf-8").strip().splitlines()
        assert content
        entry = json.loads(content[-1])
        assert entry["event"] == "unit.test_event"
        assert entry["data"]["amount"] == 1250

    def test_ring_buffer_feeds_diagnostics(self, fresh_logging: Path) -> None:
        logger = get_logger("dentivapro.tests")
        log_event(logger, logging.WARNING, "unit.diagnostic_event", item="x")
        snapshot = diagnostics_snapshot()
        assert any(entry["event"] == "unit.diagnostic_event" for entry in snapshot)

    def test_same_folder_reuses_the_configuration(self, fresh_logging: Path) -> None:
        handlers_before = list(logging.getLogger().handlers)
        again = configure_logging(fresh_logging.parent, level="DEBUG")
        assert again == fresh_logging
        assert list(logging.getLogger().handlers) == handlers_before

    def test_changing_data_folder_retargets_the_log_file(
        self, fresh_logging: Path, tmp_path: Path
    ) -> None:
        """A restore (or support work on a copied folder) must log to the new folder."""
        logger = get_logger("dentivapro.tests")
        moved = configure_logging(tmp_path / "moved", level="INFO")
        assert moved is not None and moved.parent == tmp_path / "moved"
        log_event(logger, logging.INFO, "unit.after_move")
        for handler in logging.getLogger().handlers:
            handler.flush()
        assert "unit.after_move" in moved.read_text(encoding="utf-8")
        # The previous file is closed so Windows cannot keep the folder locked.
        assert "unit.after_move" not in fresh_logging.read_text(encoding="utf-8")

    def test_close_logging_releases_the_file(self, fresh_logging: Path, tmp_path: Path) -> None:
        close_logging()
        from logging.handlers import RotatingFileHandler

        remaining = [
            handler
            for handler in logging.getLogger().handlers
            if isinstance(handler, RotatingFileHandler)
        ]
        assert remaining == []
        reopened = configure_logging(tmp_path / "after-close")
        assert reopened is not None
        assert reopened.exists()


class TestUserFacingErrors:
    def test_domain_errors_keep_their_code_and_message(self) -> None:
        error = to_user_error(PermissionDenied(permission="payment.view"))
        assert error.code == "PERMISSION_DENIED"
        assert error.title == "You do not have permission"
        assert error.action
        assert error.context["permission"] == "payment.view"

    def test_validation_error_exposes_field_details(self) -> None:
        error = to_user_error(
            ValidationError("Check the form.", fields={"phone": "Must be 11 digits"})
        )
        assert "phone" in (error.detail or "")

    def test_unexpected_errors_are_masked_but_detailed_for_support(self) -> None:
        error = to_user_error(RuntimeError("internal table dentivapro_secret failed"))
        assert error.code == "UNEXPECTED_ERROR"
        assert "internal table" not in error.message
        assert "RuntimeError" in (error.detail or "")

    def test_correlation_id_is_carried_through(self) -> None:
        error = to_user_error(ConflictError("duplicate"), correlation_id="abc123")
        assert error.correlation_id == "abc123"

    def test_every_domain_error_has_a_stable_code(self) -> None:
        for error in (
            DentivaError("x"),
            ValidationError("x"),
            PermissionDenied(),
            ConflictError("x"),
        ):
            assert error.code.isupper()
            assert error.title
