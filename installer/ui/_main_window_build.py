"""Assembling the setup window's layout.

Construction is separated from behaviour so each stays small enough to read in
one pass: this module only builds widgets and places them, and the window
module decides what they do. British spelling is used in comments. No em dashes
appear anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from installer.constants import APP_DISPLAY_NAME, APP_TAGLINE
from installer.state.model import InstallState, StateSnapshot
from installer.ui.icons import app_icon
from installer.ui.themes import (
    BUTTON_GAP,
    DANGER_ACTION,
    DIVIDER,
    DIVIDER_PX,
    HEADER_SPACING,
    HEADER_TITLE,
    HEADER_VERSION,
    ICON_PX,
    INSTALL_PATH,
    LICENCE_BUTTON,
    MARGIN_BOTTOM,
    MARGIN_SIDE,
    MARGIN_TOP,
    PRIMARY_ACTION,
    PROGRESS_BAR,
    PROGRESS_HEIGHT_PX,
    SECONDARY_ACTION,
    SECTION_SPACING,
    STATUS_LINE,
    SUBTITLE,
    TAGLINE,
)

INSTALL_LABEL = "Install"
UPGRADE_LABEL = "Upgrade to {version}"
UPGRADE_FALLBACK_LABEL = "Upgrade"
DOWNGRADE_LABEL = "Reinstall (older)"
REINSTALL_LABEL = "Reinstall"
REPAIR_LABEL = "Repair"
UNINSTALL_LABEL = "Uninstall"
CLOSE_LABEL = "Close"
LICENCE_LABEL = "Licence"

DESKTOP_LABEL = "Create a desktop shortcut"
START_MENU_LABEL = "Create a Start Menu shortcut"
LAUNCH_LABEL = f"Launch {APP_DISPLAY_NAME} when finished"
AUTOSTART_LABEL = f"Start {APP_DISPLAY_NAME} when I sign in to Windows"

WELCOME_SUBTITLE = f"Welcome to the {APP_DISPLAY_NAME} installer"
INSTALLED_SUBTITLE = f"{APP_DISPLAY_NAME} is already installed"
INSTALL_PATH_TEXT = "Install location: {path}"
VERSION_TEXT = "v{version}"
TITLE_TEXT = f"{APP_DISPLAY_NAME} Setup"


@dataclass(frozen=True, slots=True)
class WindowWidgets:
    """Every widget the window's behaviour needs to reach."""

    subtitle: QLabel
    path_label: QLabel
    desktop: QCheckBox
    start_menu: QCheckBox
    launch_on_finish: QCheckBox
    autostart: QCheckBox
    status: QLabel
    progress: QProgressBar
    licence: QPushButton
    primary: QPushButton
    repair: QPushButton
    uninstall: QPushButton
    close: QPushButton


def primary_label(snapshot: StateSnapshot) -> str:
    """Return the primary button caption for the detected state."""
    if snapshot.state == InstallState.NOT_INSTALLED:
        return INSTALL_LABEL
    if snapshot.state == InstallState.UPGRADE:
        version = snapshot.bundled_version
        if version:
            return UPGRADE_LABEL.format(version=version)
        return UPGRADE_FALLBACK_LABEL
    if snapshot.state == InstallState.DOWNGRADE:
        return DOWNGRADE_LABEL
    return REINSTALL_LABEL


def subtitle_text(snapshot: StateSnapshot) -> str:
    """Return the subtitle reflecting whether this is a fresh install."""
    if snapshot.installed:
        return INSTALLED_SUBTITLE
    return WELCOME_SUBTITLE


def _build_header(widgets_licence: QPushButton, version: str) -> QHBoxLayout:
    """Build the header row: icon, title and version, with a Licence button."""
    header = QHBoxLayout()
    header.setSpacing(HEADER_SPACING)

    icon = app_icon()
    if not icon.isNull():
        badge = QLabel()
        badge.setPixmap(icon.pixmap(QSize(ICON_PX, ICON_PX)))
        header.addWidget(badge)

    title = QLabel(TITLE_TEXT)
    title.setObjectName(HEADER_TITLE)
    header.addWidget(title)

    if version:
        version_label = QLabel(VERSION_TEXT.format(version=version))
        version_label.setObjectName(HEADER_VERSION)
        version_label.setAlignment(
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft
        )
        header.addWidget(version_label)

    header.addStretch()
    header.addWidget(widgets_licence)
    return header


def _build_buttons(widgets: WindowWidgets) -> QHBoxLayout:
    """Build the action row: Uninstall, then Repair, primary and Close."""
    row = QHBoxLayout()
    row.setSpacing(BUTTON_GAP)
    row.addWidget(widgets.uninstall)
    row.addStretch()
    row.addWidget(widgets.repair)
    row.addWidget(widgets.primary)
    row.addWidget(widgets.close)
    return row


def _make_widgets(snapshot: StateSnapshot) -> WindowWidgets:
    """Create every widget, named and styled, before any of it is placed."""
    subtitle = QLabel(subtitle_text(snapshot))
    subtitle.setObjectName(SUBTITLE)
    subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)

    path_label = QLabel(INSTALL_PATH_TEXT.format(path=snapshot.install_dir))
    path_label.setObjectName(INSTALL_PATH)
    path_label.setWordWrap(True)

    status = QLabel("")
    status.setObjectName(STATUS_LINE)
    status.setWordWrap(True)

    progress = QProgressBar()
    progress.setObjectName(PROGRESS_BAR)
    progress.setFixedHeight(PROGRESS_HEIGHT_PX)
    progress.setTextVisible(False)
    progress.setVisible(False)

    primary = QPushButton(primary_label(snapshot))
    primary.setObjectName(PRIMARY_ACTION)
    repair = QPushButton(REPAIR_LABEL)
    repair.setObjectName(SECONDARY_ACTION)
    uninstall = QPushButton(UNINSTALL_LABEL)
    uninstall.setObjectName(DANGER_ACTION)
    close = QPushButton(CLOSE_LABEL)
    close.setObjectName(SECONDARY_ACTION)
    licence = QPushButton(LICENCE_LABEL)
    licence.setObjectName(LICENCE_BUTTON)

    desktop = QCheckBox(DESKTOP_LABEL)
    desktop.setChecked(True)
    start_menu = QCheckBox(START_MENU_LABEL)
    start_menu.setChecked(True)
    launch_on_finish = QCheckBox(LAUNCH_LABEL)
    launch_on_finish.setChecked(True)
    autostart = QCheckBox(AUTOSTART_LABEL)
    autostart.setChecked(snapshot.autostart)

    return WindowWidgets(
        subtitle=subtitle,
        path_label=path_label,
        desktop=desktop,
        start_menu=start_menu,
        launch_on_finish=launch_on_finish,
        autostart=autostart,
        status=status,
        progress=progress,
        licence=licence,
        primary=primary,
        repair=repair,
        uninstall=uninstall,
        close=close,
    )


def build_window(window: QWidget, snapshot: StateSnapshot) -> WindowWidgets:
    """Create the window's widgets and lay them out in one column."""
    widgets = _make_widgets(snapshot)

    layout = QVBoxLayout(window)
    layout.setContentsMargins(MARGIN_SIDE, MARGIN_TOP, MARGIN_SIDE, MARGIN_BOTTOM)
    layout.setSpacing(SECTION_SPACING)

    layout.addLayout(_build_header(widgets.licence, snapshot.bundled_version))
    layout.addWidget(widgets.subtitle)

    tagline = QLabel(APP_TAGLINE)
    tagline.setObjectName(TAGLINE)
    tagline.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    layout.addWidget(tagline)

    divider = QFrame()
    divider.setObjectName(DIVIDER)
    divider.setFixedHeight(DIVIDER_PX)
    layout.addWidget(divider)

    layout.addWidget(widgets.path_label)
    layout.addWidget(widgets.desktop)
    layout.addWidget(widgets.start_menu)
    layout.addWidget(widgets.launch_on_finish)
    layout.addWidget(widgets.autostart)
    layout.addWidget(widgets.progress)
    layout.addWidget(widgets.status)

    layout.addStretch()
    layout.addLayout(_build_buttons(widgets))
    return widgets
