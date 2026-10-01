"""The About screen.

Identifies the product, its version and its creator (as required by the specification), shows where
clinic data lives, and renders the bundled open-source notices. It deliberately avoids exposing
internal technical detail beyond what an administrator needs for support.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dentivapro.core.i18n import creator_line, t
from dentivapro.ui.components.cards import Card
from dentivapro.ui.components.page import PageHeader
from dentivapro.ui.components.primitives import Text
from dentivapro.ui.design.icons import icon
from dentivapro.ui.design.theme import theme

if TYPE_CHECKING:
    from collections.abc import Mapping
from dentivapro.ui.design.tokens import tokens
from dentivapro.version import (
    APP_NAME,
    CREATOR_NAME,
    PRODUCT_DESCRIPTION,
    RELEASE_CHANNEL,
    __version__,
)

NOTICES_DIR = Path(__file__).resolve().parents[2] / "assets" / "notices"

NOTICE_FILES: tuple[tuple[str, str], ...] = (
    ("Inter (UI typeface)", "OFL-1.1-Inter.txt"),
    ("Noto Sans Bengali (Bangla typeface)", "OFL-1.1-NotoSansBengali.txt"),
    ("Lucide icons", "Lucide-ISC-LICENSE.txt"),
)


#: The machine-dependent rows of the system-information card, and the diagnostic keys that override them.
_DIAGNOSTIC_KEYS = ("python", "qt", "platform", "build")


def _environment_values(overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    """Real values for the system-information card, with any caller-supplied overrides applied."""
    values = {
        "python": platform.python_version(),
        "qt": pyside_version,
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "build": f"{sys.version_info.major}.{sys.version_info.minor}",
    }
    if overrides:
        values.update({key: value for key, value in overrides.items() if key in values})
    return values


class AboutScreen(QWidget):
    """Product identity, version and licence information."""

    def __init__(
        self,
        *,
        paths: object | None = None,
        diagnostics: Mapping[str, str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._paths = paths
        #: Machine-dependent rows (python/Qt/platform/build). Injectable so the About screen's layout can
        #: be golden-tested without the baseline depending on the machine that produced it.
        self._diagnostics = diagnostics

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            tokens().spacing.screen_gutter,
            tokens().spacing.xl,
            tokens().spacing.screen_gutter,
            tokens().spacing.xl,
        )
        outer.setSpacing(tokens().spacing.xl)

        outer.addWidget(
            PageHeader(
                t("about.title"),
                PRODUCT_DESCRIPTION,
                parent=self,
            )
        )

        content = QWidget(self)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(tokens().spacing.xl)
        content_layout.addWidget(self._identity_card(content))
        content_layout.addWidget(self._system_card(content))
        content_layout.addWidget(self._notices_card(content))
        content_layout.addWidget(self._copyright_card(content))
        content_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    # ---- cards -------------------------------------------------------------
    def _identity_card(self, parent: QWidget) -> Card:
        card = Card(padding=tokens().spacing.xl, parent=parent)
        lockup = QWidget(card.body)
        lockup_layout = QHBoxLayout(lockup)
        lockup_layout.setContentsMargins(0, 0, 0, 0)
        lockup_layout.setSpacing(tokens().spacing.xl)
        mark = QLabel(lockup)
        mark_size = tokens().metrics.icon_xl * 2
        mark.setFixedSize(mark_size, mark_size)
        mark.setPixmap(
            icon("tooth", mark_size, theme().colour("accent_600")).pixmap(
                QSize(mark_size, mark_size)
            )
        )
        lockup_layout.addWidget(mark, alignment=Qt.AlignmentFlag.AlignTop)
        lockup_text = QWidget(lockup)
        text_layout = QVBoxLayout(lockup_text)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(tokens().spacing.xs)
        text_layout.addWidget(Text(APP_NAME, role="h2"))
        text_layout.addWidget(Text(PRODUCT_DESCRIPTION, role="secondary", word_wrap=True))
        text_layout.addWidget(Text(f"Version {__version__} · {RELEASE_CHANNEL}", role="mono"))
        lockup_layout.addWidget(lockup_text, 1)
        card.add(lockup)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(tokens().spacing.xl)
        form.setVerticalSpacing(tokens().spacing.md)
        form.addRow(
            Text(t("about.created_by"), role="label"),
            Text(creator_line(), role="body", selectable=True),
        )
        form.addRow(
            Text(t("about.licence"), role="label"),
            Text(t("about.licence_value"), role="body"),
        )
        holder = QWidget(card.body)
        holder.setLayout(form)
        card.add(holder)
        return card

    def _system_card(self, parent: QWidget) -> Card:
        card = Card(
            title=t("about.system"),
            subtitle="Information an administrator or support engineer may need.",
            icon_name="hard-drive",
            parent=parent,
        )
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(tokens().spacing.xl)
        form.setVerticalSpacing(tokens().spacing.md)

        data_root = "—"
        database = "—"
        if self._paths is not None:
            data_root = str(getattr(self._paths, "data_root", "—"))
            database = str(getattr(self._paths, "database_file", "—"))

        form.addRow(
            Text(t("about.data_location"), role="label"),
            Text(data_root, role="mono", word_wrap=True, selectable=True),
        )
        form.addRow(
            Text(t("about.database"), role="label"),
            Text(database, role="mono", word_wrap=True, selectable=True),
        )
        environment = _environment_values(self._diagnostics)
        form.addRow(
            Text(t("about.python_version"), role="label"),
            Text(environment["python"], role="mono", selectable=True),
        )
        form.addRow(
            Text(t("about.qt_version"), role="label"),
            Text(environment["qt"], role="mono", selectable=True),
        )
        form.addRow(
            Text(t("about.platform"), role="label"),
            Text(environment["platform"], role="body"),
        )
        form.addRow(
            Text(t("about.build"), role="label"),
            Text(environment["build"], role="mono"),
        )
        holder = QWidget(card.body)
        holder.setLayout(form)
        card.add(holder)
        return card

    def _notices_card(self, parent: QWidget) -> Card:
        card = Card(
            title=t("about.notices"),
            subtitle=t("about.notices_hint"),
            icon_name="file-text",
            parent=parent,
        )
        for title, filename in NOTICE_FILES:
            text = self._read_notice(filename)
            card.add(Text(title, role="h3"))
            notice_label = Text(text, role="caption", selectable=True, word_wrap=False)
            notice_label.setTextFormat(Qt.TextFormat.PlainText)
            scroll = QScrollArea(card.body)
            scroll.setWidgetResizable(False)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setMaximumHeight(150)
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.addWidget(notice_label)
            scroll.setWidget(holder)
            card.add(scroll)
        return card

    def _copyright_card(self, parent: QWidget) -> Card:
        card = Card(parent=parent)
        card.add(
            Text(
                t("about.copyright", creator=CREATOR_NAME),
                role="caption",
                word_wrap=True,
            )
        )
        return card

    @staticmethod
    def _read_notice(filename: str) -> str:
        path = NOTICES_DIR / filename
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return f"({filename} is not available in this build)"
