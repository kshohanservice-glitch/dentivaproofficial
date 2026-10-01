"""Rendering tests for the shell: golden images, responsive sizes, high DPI, state coverage.

The product must look right on the range of Windows displays a clinic actually uses (1366×768 laptops
through 1920×1080 desktops), at 100 %–200 % scaling, and in every state a screen can be in.

Every render is written to ``tests/ui/artifacts/screens/`` for human review and compared against the
platform's committed golden fingerprint (see ``tests/ui/golden_store.py`` for why fingerprints are used
instead of raw pixels, and for the promote-a-new-baseline workflow). Linux goldens are committed from
this sandbox; the Windows baseline is produced on ``windows-latest`` CI, where the renders are also
uploaded as a build artifact.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from golden_store import (  # the golden helper lives beside the UI tests
    PROMOTE_COMMAND,
    compare,
    distinct_colours,
    fingerprint,
    load_golden,
    platform_key,
    save_render,
)
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage

from dentivapro.ui.design.tokens import tokens
from dentivapro.ui.shell.navigation import all_entries

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

pytestmark = pytest.mark.ui

#: Window sizes a clinic uses: a small laptop, the default, a common desktop and a large monitor.
WINDOW_SIZES: tuple[tuple[int, int], ...] = (
    (1024, 720),
    (1360, 860),
    (1600, 900),
    (1920, 1080),
)

#: Windows display scales the product must support (Dentiva Pro is DPI-aware).
SCALES: tuple[float, ...] = (1.0, 1.25, 1.5, 2.0)


def _render(window: QWidget, size: QSize, *, device_pixel_ratio: float = 1.0) -> QImage:
    """Render *window* at *size* into an image at the requested device pixel ratio."""
    window.resize(size)
    window.repaint()
    image = QImage(
        int(size.width() * device_pixel_ratio),
        int(size.height() * device_pixel_ratio),
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.setDevicePixelRatio(device_pixel_ratio)
    image.fill(0)
    window.render(image)
    return image


def _capture(image: QImage, name: str) -> str | None:
    """Write the render for review and compare it with the committed golden.

    Returns a description of the render when this platform has no approved golden for *name* yet, so the
    caller can report a skip instead of pretending the render was verified. Raises on a real mismatch.
    """
    png, _ = save_render(image, name)
    rendered = fingerprint(image)
    golden = load_golden(name)
    if golden is None:
        return f"{name} ({png})"
    assert distinct_colours(rendered) > 4, f"{name} rendered (almost) blank"
    reasons = compare(rendered, golden)
    assert not reasons, f"golden mismatch for {name}: " + "; ".join(reasons)
    return None


def _report_missing(missing: list[str | None]) -> None:
    """Skip with instructions when renders have no approved golden for this platform."""
    names = [name for name in missing if name]
    if names:
        pytest.skip(
            f"no approved {platform_key()} golden baseline for {len(names)} render(s): "
            + "; ".join(names)
            + f" — review the PNGs in tests/ui/artifacts/screens/ and run: {PROMOTE_COMMAND}"
        )


class TestResponsiveRendering:
    def test_shell_renders_at_every_supported_size(self, golden_window) -> None:
        missing: list[str | None] = []
        for width, height in WINDOW_SIZES:
            image = _render(golden_window, QSize(width, height))
            assert image.width() == width and image.height() == height
            missing.append(_capture(image, f"shell-{width}x{height}"))
        _report_missing(missing)

    def test_narrowest_supported_window_keeps_the_navigation_usable(self, golden_window) -> None:
        image = _render(golden_window, QSize(1024, 720))

        metrics = tokens().metrics
        assert golden_window.sidebar.width() in (
            metrics.sidebar_width,
            metrics.sidebar_collapsed_width,
        )
        assert golden_window.header.width() == 1024
        # The shell must never gain horizontal scrollbars at the smallest supported size.
        assert golden_window.centralWidget().width() <= 1024
        _report_missing([_capture(image, "shell-1024x720")])

    def test_narrow_window_uses_the_compact_header(self, golden_window) -> None:
        """The header must not force the window wider than a 1024 px laptop screen."""
        from PySide6.QtCore import Qt

        golden_window.resize(QSize(1024, 720))
        golden_window.header.resize(QSize(1024, 60))
        assert golden_window.header._compact is True  # noqa: SLF001
        style = golden_window.header._user_button.toolButtonStyle()  # noqa: SLF001
        assert style == Qt.ToolButtonStyle.ToolButtonIconOnly
        assert golden_window.header._search_button.text() == ""  # noqa: SLF001
        assert golden_window.header.minimumSizeHint().width() <= 1024
        _report_missing(
            [_capture(_render(golden_window, QSize(1024, 720)), "shell-1024x720-compact-header")]
        )

    def test_collapsed_sidebar_renders(self, golden_window) -> None:
        golden_window.repaint()
        golden_window.sidebar.toggle_collapsed()
        assert golden_window.sidebar.width() == tokens().metrics.sidebar_collapsed_width
        _report_missing(
            [_capture(_render(golden_window, QSize(1360, 860)), "shell-collapsed-sidebar")]
        )

    def test_window_sizes_do_not_clip_the_header_or_status_bar(self, golden_window) -> None:
        for width, height in WINDOW_SIZES:
            image = _render(golden_window, QSize(width, height))
            assert golden_window.header.geometry().bottom() <= height
            assert golden_window.statusBar().geometry().bottom() <= height
            assert image.height() == height


class TestHighDpiRendering:
    @pytest.mark.parametrize("ratio", SCALES)
    def test_shell_renders_at_every_supported_scale(self, golden_window, ratio: float) -> None:
        image = _render(golden_window, QSize(1360, 860), device_pixel_ratio=ratio)

        assert image.devicePixelRatio() == pytest.approx(ratio)
        assert image.width() == int(1360 * ratio)
        # 100 % shares the plain shell golden; the scaled renders have their own baselines.
        name = "shell-1360x860" if ratio == 1.0 else f"shell-1360x860-scale{int(ratio * 100)}"
        _report_missing([_capture(image, name)])

    def test_icons_are_crisp_at_150_percent(self, golden_window) -> None:
        """An icon rendered for a scaled display must keep its logical size."""
        from dentivapro.ui.design.icons import icons
        from dentivapro.ui.design.tokens import LIGHT

        pixmap = icons().pixmap("settings", 20, LIGHT.palette.ink_600, device_pixel_ratio=1.5)
        assert pixmap.devicePixelRatio() == pytest.approx(1.5)
        assert pixmap.width() == 30

    def test_table_row_height_does_not_collapse_at_scale(self, qt_app) -> None:
        from dentivapro.ui.components.data_table import Column, DataTable

        table = DataTable((Column("name", "Name", stretch=True),), parent=None)
        table.set_rows([{"name": f"Patient {index}"} for index in range(50)])
        table.resize(800, 400)
        table.show()
        qt_app.processEvents()
        image = QImage(QSize(800, 400), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        table.render(image)
        # 50 rows do not fit in 400 px, so the view must offer scrolling rather than hiding rows.
        assert table.row_count == 50
        assert table.view.verticalScrollBar().maximum() > 0
        table.close()
        _report_missing([_capture(image, "component-data-table")])


class TestScreenStates:
    def test_every_route_renders_and_is_saved_for_review(self, golden_window) -> None:
        """Every destination is rendered to an artifact; a blank render would be a defect."""
        for entry in all_entries():
            assert golden_window.navigate(entry.route) is True
            image = _render(golden_window, QSize(1360, 860))
            save_render(image, f"route-{entry.route}", golden=False)
            assert distinct_colours(fingerprint(image)) > 4, entry.route

    def test_about_screen_matches_its_golden(self, golden_window) -> None:
        assert golden_window.navigate("about") is True
        _report_missing([_capture(_render(golden_window, QSize(1360, 860)), "screen-about")])

    def test_pending_module_screen_matches_its_golden(self, golden_window) -> None:
        assert golden_window.navigate("patients") is True
        screen = golden_window._current_screen  # noqa: SLF001
        assert screen is not None
        assert screen._state.property("developmentState") is True  # noqa: SLF001
        _report_missing(
            [_capture(_render(golden_window, QSize(1360, 860)), "screen-pending-patients")]
        )

    def test_toast_overlay_matches_its_golden(self, golden_window) -> None:
        golden_window.toasts.success("Patient saved", "P-000123 was registered.")
        assert golden_window.toasts.visible_count >= 1
        _report_missing([_capture(_render(golden_window, QSize(1360, 860)), "shell-toast")])

    def test_foundation_banner_is_part_of_the_render(self, golden_window) -> None:
        image = _render(golden_window, QSize(1360, 860))
        banner = golden_window._foundation_banner  # noqa: SLF001
        assert banner.isVisible()
        assert banner.geometry().width() > 0
        save_render(image, "shell-foundation-banner", golden=False)


def test_golden_helper_paths_live_under_tests_ui() -> None:
    """A guard so the goldens cannot silently move out of the repository's ignored/committed layout."""
    from golden_store import ARTIFACTS_DIR, GOLDENS_DIR

    root = Path(__file__).resolve().parent
    assert root / "goldens" == GOLDENS_DIR
    assert root / "artifacts" / "screens" == ARTIFACTS_DIR
