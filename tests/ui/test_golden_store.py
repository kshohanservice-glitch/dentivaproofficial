"""Unit tests for the golden-image helper itself.

The golden store is the gate that protects every other UI render, so it must fail when the picture
changes and pass when it does not. These tests use small synthetic images instead of the real shell so
they are fast and independent of the design system.
"""

from __future__ import annotations

import pytest
from golden_store import (
    CHANNEL_TOLERANCE,
    GRID,
    MAX_MISMATCHED_RATIO,
    compare,
    distinct_colours,
    fingerprint,
    load_golden,
    platform_key,
)
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter

pytestmark = pytest.mark.ui


def _make_image(
    colour: str = "#F6F8FA", *, block: QRect | None = None, size: tuple[int, int] = (320, 240)
) -> QImage:
    image = QImage(*size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(colour))
    if block is not None:
        painter = QPainter(image)
        painter.fillRect(block, QColor("#0F766E"))
        painter.end()
    return image


def test_platform_key_is_one_of_the_baseline_folders() -> None:
    assert platform_key() in {"linux", "windows", "macos"}


def test_fingerprint_records_size_and_grid() -> None:
    rendered = fingerprint(_make_image())
    assert (rendered["width"], rendered["height"]) == (320, 240)
    assert rendered["grid"] == list(GRID)
    assert len(rendered["cells"]) == GRID[0] * GRID[1]


def test_identical_images_match() -> None:
    assert compare(fingerprint(_make_image()), fingerprint(_make_image())) == []


def test_tiny_rendering_noise_is_tolerated() -> None:
    """Anti-aliasing differences between platforms must not fail the gate."""
    golden = fingerprint(_make_image())
    noisy = fingerprint(_make_image("#F5F7F9"))  # 1/255 per channel
    assert compare(noisy, golden) == []


def test_a_moved_element_is_detected() -> None:
    golden = fingerprint(_make_image(block=QRect(20, 20, 120, 80)))
    shifted = fingerprint(_make_image(block=QRect(20, 140, 120, 80)))
    reasons = compare(shifted, golden)
    assert reasons, "a block moving by 120 px must fail the golden comparison"
    assert "fingerprint cells changed" in reasons[0]


def test_a_different_size_is_detected() -> None:
    reasons = compare(
        fingerprint(_make_image(size=(320, 240))), fingerprint(_make_image(size=(640, 240)))
    )
    assert reasons and "size changed" in reasons[0]


def test_a_missing_golden_is_reported_rather_than_guessed() -> None:
    assert load_golden("this-golden-does-not-exist") is None


def test_a_large_colour_shift_is_detected() -> None:
    golden = fingerprint(_make_image("#F6F8FA"))
    dark = fingerprint(_make_image("#111827"))
    assert compare(dark, golden)


def test_tolerances_are_documented_constants(value: int = CHANNEL_TOLERANCE) -> None:
    assert value > 0
    assert 0 < MAX_MISMATCHED_RATIO < 0.5


def test_distinct_colours_measures_the_grid() -> None:
    flat = fingerprint(_make_image())
    assert distinct_colours(flat) == 1
    with_block = fingerprint(_make_image(block=QRect(0, 0, 160, 120)))
    assert distinct_colours(with_block) > 1
