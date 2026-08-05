"""Identity, layout and registry constants for the o7Debrief setup program.

Every name the installer writes to disk or to the registry is declared here, so
a rename is a single edit and no module carries an inline literal. British
spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

# --- product identity -------------------------------------------------------

# The spaceless identifier used for the payload directory, install path and exe.
APP_NAME = "o7Debrief"
# The display name shown in all installer text and in the Apps list.
APP_DISPLAY_NAME = "o7 Debrief"
APP_TAGLINE = "Commander Mission Debrief"
APP_PUBLISHER = "Oliver Ernster"
APP_URL = "https://oernster.github.io/o7Debrief/"

EXE_NAME = "o7Debrief.exe"
EXE_SUFFIX = ".exe"

# --- payload layout ---------------------------------------------------------

# Produced by buildinstaller.py: payload/o7Debrief/ holds the bundle's
# non-binary files, payload/o7Debrief.zip holds the full bundle for deployment
# and payload/LICENSE holds the licence text.
PAYLOAD_DIR_NAME = "payload"
PAYLOAD_ARCHIVE_NAME = "o7Debrief.zip"
LICENSE_FILE_NAME = "LICENSE"
VERSION_FILE_NAME = "VERSION"

ICON_SUBPATH = ("assets", "o7Debrief.png")
# The multi-size .ico, used for shortcuts and the Apps-list DisplayIcon so the
# small sizes that Windows search and the taskbar render are present.
SHORTCUT_ICON_SUBPATH = ("assets", "o7debrief.ico")

# --- per-user locations (no administrator rights required) ------------------

ENV_LOCALAPPDATA = "LOCALAPPDATA"
ENV_APPDATA = "APPDATA"
PROGRAMS_DIR_NAME = "Programs"
START_MENU_SUBPATH = ("Microsoft", "Windows", "Start Menu", "Programs")
DESKTOP_DIR_NAME = "Desktop"
SHORTCUT_EXT = ".lnk"
# The per-user state directory the application writes (preferences, ranks).
STATE_DIR_NAME = "o7Debrief"

# --- the registered uninstaller ---------------------------------------------

# A copy of the setup program is placed under the install root, so
# "Apps & features" can re-run it with --uninstall.
UNINSTALLER_SUBDIR = "_uninstall"
UNINSTALLER_NAME = "o7DebriefSetup.exe"
UNINSTALL_FLAG = "--uninstall"
# Under a Nuitka onefile build sys.executable is the unpacked temporary
# bootstrap, so the original launcher is discovered through this instead.
NUITKA_ONEFILE_ENV = "NUITKA_ONEFILE_BINARY"

# --- registry keys (all under HKCU) -----------------------------------------

# This is what makes the app appear in "Apps & features" with a working
# Uninstall button.
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\o7Debrief"
# Launching the app at Windows sign-in, per user so no admin rights are needed.
RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "o7Debrief"
# The app registers its notification name and icon under this Application User
# Model ID at startup; uninstall removes that registration. Must match main.py.
APP_AUMID = "OliverErnster.o7Debrief"
INSTALLER_AUMID = "OliverErnster.o7Debrief.Installer"
AUMID_CLASSES_SUBKEY = r"Software\Classes\AppUserModelId"

# --- diagnostics ------------------------------------------------------------

# A console-disabled onefile shows no traceback when it dies, so unhandled
# exceptions are appended to this file under the temporary directory.
INSTALLER_LOG_NAME = "o7debrief-installer.log"

# Used when the bundled VERSION file is missing or unreadable.
FALLBACK_VERSION = "0.0.0"
