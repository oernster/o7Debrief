"""The installer's palette, stylesheet and layout constants.

The dark-dossier palette mirrors the o7Debrief splash and report HUD, so the
setup program feels of a piece with the application it deploys. The theme is the
app's own and travels with it: only the functionality is shared with the other
installers in the portfolio. British spelling is used in comments. No em dashes
appear anywhere.
"""

from __future__ import annotations

# --- palette ----------------------------------------------------------------

BACKGROUND = "#0d0d10"
SURFACE = "#16161d"
EDGE = "#2a2a33"
ACCENT = "#f07b05"
ACCENT_SOFT = "#f8a24a"
TEXT = "#d7d7da"
MUTED = "#8a8a93"
DANGER = "#7a1f25"
DANGER_HOVER = "#94262e"

# --- geometry ---------------------------------------------------------------

WINDOW_WIDTH = 620
WINDOW_HEIGHT = 600
LICENCE_DIALOG_HEIGHT = 540
LICENCE_FONT_PX = 12
ICON_PX = 56
DIVIDER_PX = 1
BORDER_PX = 1
TEXT_PADDING_PX = 8
SIDES = 2
WIDTH_SAFETY_PX = 8
MARGIN_SIDE = 36
MARGIN_TOP = 28
MARGIN_BOTTOM = 24
DIALOG_MARGIN = 20
SECTION_SPACING = 14
HEADER_SPACING = 14
# The version suffix rendered inline beside the header title. It is a rich-text
# span inside the title's own label rather than a second widget, because a Qt
# layout cannot align two widgets on a shared text baseline: the version sat
# thirteen pixels below the title, dropped to the bottom of a row whose height
# the icon sets. Inline spans share a baseline by construction, so the whole
# class of misalignment goes away rather than being nudged into place.
HEADER_VERSION_PX = 13
BUTTON_GAP = 10
PROGRESS_HEIGHT_PX = 10

# --- object names, so the stylesheet and the widgets agree ------------------

HEADER_TITLE = "HeaderTitle"
SUBTITLE = "SubTitle"
TAGLINE = "Tagline"
INSTALL_PATH = "InstallPath"
STATUS_LINE = "StatusLine"
DIVIDER = "Divider"
LICENCE_BUTTON = "LicenceButton"
LICENCE_VIEW = "LicenceView"
PRIMARY_ACTION = "PrimaryAction"
SECONDARY_ACTION = "SecondaryAction"
DANGER_ACTION = "DangerAction"
PROGRESS_BAR = "InstallProgress"

STYLESHEET = f"""
QWidget {{ background: {BACKGROUND}; color: {TEXT}; font-family: 'Segoe UI'; }}
QLabel#{HEADER_TITLE} {{ font-size: 30px; font-weight: 700; color: {ACCENT}; }}
QLabel#{SUBTITLE} {{ font-size: 18px; font-weight: 700; color: {ACCENT}; }}
QLabel#{TAGLINE} {{ font-size: 13px; color: {MUTED}; }}
QLabel#{INSTALL_PATH} {{ font-size: 12px; color: {MUTED}; }}
QLabel#{STATUS_LINE} {{ font-size: 13px; color: {TEXT}; }}
QFrame#{DIVIDER} {{ background: {EDGE}; border: none; }}
QCheckBox {{ spacing: 10px; font-size: 13px; color: {TEXT}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QProgressBar#{PROGRESS_BAR} {{
    background: {SURFACE}; border: {BORDER_PX}px solid {EDGE};
    border-radius: 5px; height: {PROGRESS_HEIGHT_PX}px; text-align: center;
    color: transparent;
}}
QProgressBar#{PROGRESS_BAR}::chunk {{ background: {ACCENT}; border-radius: 4px; }}
QPushButton#{LICENCE_BUTTON} {{
    background: {SURFACE}; color: {TEXT}; border: 1px solid {EDGE};
    padding: 8px 16px; border-radius: 16px; font-weight: 600;
}}
QPushButton#{LICENCE_BUTTON}:enabled:hover {{ background: {EDGE}; }}
QPushButton#{PRIMARY_ACTION} {{
    background: {ACCENT}; color: {BACKGROUND}; border: none;
    padding: 12px 28px; border-radius: 22px; font-size: 14px;
    font-weight: 700; min-width: 150px;
}}
QPushButton#{PRIMARY_ACTION}:enabled:hover {{ background: {ACCENT_SOFT}; }}
QPushButton#{PRIMARY_ACTION}:disabled {{ background: {EDGE}; color: {MUTED}; }}
QPushButton#{SECONDARY_ACTION} {{
    background: {SURFACE}; color: {TEXT}; border: 1px solid {EDGE};
    padding: 12px 22px; border-radius: 22px; font-size: 13px; font-weight: 600;
}}
QPushButton#{SECONDARY_ACTION}:enabled:hover {{ background: {EDGE}; }}
QPushButton#{SECONDARY_ACTION}:disabled {{ color: {MUTED}; }}
QPushButton#{DANGER_ACTION} {{
    background: {DANGER}; color: {TEXT}; border: none;
    padding: 12px 22px; border-radius: 22px; font-size: 13px; font-weight: 600;
}}
QPushButton#{DANGER_ACTION}:enabled:hover {{ background: {DANGER_HOVER}; }}
QPushButton#{DANGER_ACTION}:disabled {{ background: {EDGE}; color: {MUTED}; }}
QTextEdit {{
    background: {SURFACE}; border: {BORDER_PX}px solid {EDGE};
    border-radius: 10px; color: {TEXT}; padding: {TEXT_PADDING_PX}px;
}}
QTextEdit#{LICENCE_VIEW} {{
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: {LICENCE_FONT_PX}px;
}}
QDialog {{ background: {BACKGROUND}; }}
"""
