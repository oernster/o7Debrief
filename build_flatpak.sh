#!/usr/bin/env bash
# build_flatpak.sh - Build o7 Debrief as a Flatpak
#
# Uses org.freedesktop.Platform//25.08 (Python 3.13, glibc 2.42).
# o7 Debrief is a pure PySide6 + Jinja2 app: no native toolchains, no model
# downloads.  The wheels are pre-downloaded on the host, then installed inside
# the sandbox from those local wheels with --no-index, so the build is offline.
#
# Usage:
#   ./build_flatpak.sh             - build, install locally, AND produce o7debrief.flatpak
#   ./build_flatpak.sh --no-bundle - build + install only (skip the distributable bundle)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ ! -f venv/bin/activate ]]; then
    echo "ERROR: no virtual environment at ${SCRIPT_DIR}/venv" >&2
    echo "Create one first:  python3 -m venv venv" >&2
    echo "                   ./venv/bin/pip install -r requirements-dev.txt" >&2
    exit 1
fi
source venv/bin/activate

APP_ID="uk.co.oernster.o7Debrief"
APP_VERSION=$(tr -d '[:space:]' < VERSION)
BUNDLE="o7debrief.flatpak"
BUILD_DIR=".flatpak-build"
REPO_DIR=".flatpak-repo"
MANIFEST="${APP_ID}.yml"

RUNTIME="org.freedesktop.Platform"
SDK="org.freedesktop.Sdk"
RUNTIME_VERSION="25.08"

# Python version shipped by the runtime above.  Used to build the site-packages
# path the launcher exports; keep it in sync with RUNTIME_VERSION.
PYTHON_MM="3.13"

# Wheels are tagged for the runtime's Python and glibc.  pip does NOT widen a
# --platform tag to the older manylinux tags, so every tag we accept has to be
# listed: PySide6/shiboken6 ship manylinux_2_34 while the pure-Python wheels
# (Jinja2, MarkupSafe) are any-tagged.  The runtime's glibc is newer than all.
WHEEL_PYTHON="3.13"
WHEEL_PLATFORMS=(
    manylinux_2_34_x86_64
    manylinux_2_28_x86_64
    manylinux_2_17_x86_64
)

# The distributable bundle is the whole point of this script, so it is built by
# default.  Pass --no-bundle to skip it and only build + install locally.
MAKE_BUNDLE=1
for arg in "$@"; do
    if [[ "$arg" == "--no-bundle" ]]; then MAKE_BUNDLE=0; fi
done

# ── Colour helpers ────────────────────────────────────────────────────────────
bold=$(tput bold 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)
section() { echo; echo "${bold}=== $* ===${reset}"; }

run_with_spinner() {
    local label="$1" watch=""
    shift
    if [[ "${1:-}" == "--watch" ]]; then watch="$2"; shift 2; fi
    if [[ "${1:-}" == "--" ]]; then shift; fi
    "$@" &
    local pid=$! i=0 spin='⣾⣽⣻⢿⡿⣟⣯⣷'
    # The spinner rewrites one line with a carriage return, which only reads as
    # a spinner on a terminal.  Redirected to a file or a pipe there is nothing
    # to rewrite, so every frame lands as its own line and buries the log; in
    # that case announce the step once and wait quietly.
    # 'wait' is read inside an if so that set -e does not abort the script
    # before the outcome line is printed; the non-zero code is returned instead.
    local rc=0
    if [[ ! -t 1 ]]; then
        echo "  ... ${label}"
        if wait "$pid"; then rc=0; else rc=$?; fi
        [[ $rc -eq 0 ]] && echo "  OK   ${label}" || echo "  FAIL ${label}"
        return $rc
    fi
    while kill -0 "$pid" 2>/dev/null; do
        local extra=""
        if [[ -n "$watch" && -f "$watch" ]]; then
            extra="  ($(du -sh "$watch" 2>/dev/null | cut -f1) written)"
        fi
        printf "\r  %s  %s%s" "${spin:$((i % ${#spin})):1}" "$label" "$extra"
        i=$((i + 1)); sleep 0.3
    done
    if wait "$pid"; then rc=0; else rc=$?; fi
    [[ $rc -eq 0 ]] && printf "\r  ✓  %-72s\n" "$label" \
                     || printf "\r  ✗  %-72s\n" "$label"
    return $rc
}

# ── Tool checks ───────────────────────────────────────────────────────────────
section "Checking dependencies"
install_if_missing() {
    local pkg="$1"
    if ! command -v "$pkg" &>/dev/null; then
        echo "  $pkg not found - installing..."
        if   command -v apt-get &>/dev/null; then sudo apt-get update -qq && sudo apt-get install -y "$pkg"
        elif command -v dnf    &>/dev/null; then sudo dnf install -y "$pkg"
        elif command -v pacman &>/dev/null; then sudo pacman -Sy --noconfirm "$pkg"
        else echo "ERROR: unsupported package manager" >&2; exit 1; fi
    else echo "  $pkg: OK"; fi
}
install_if_missing flatpak
install_if_missing flatpak-builder

# Pillow is a BUILD dependency only (it derives the hicolor icon set from the
# master PNG); the app itself never imports it, so it is not in requirements.txt
# and a venv created from the runtime requirements alone will not have it.
if python3 -c "import PIL" &>/dev/null; then
    echo "  Pillow: OK"
else
    echo "  Pillow not found in the venv - installing..."
    pip install -q Pillow
fi

# ── Flatpak remote + runtime ──────────────────────────────────────────────────
section "Configuring Flathub remote"
flatpak remote-add --if-not-exists --user flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo

section "Installing runtime and SDK (${RUNTIME_VERSION})"
flatpak install --user --noninteractive flathub \
    "${RUNTIME}//${RUNTIME_VERSION}" \
    "${SDK}//${RUNTIME_VERSION}" \
    || true

# ── Pre-download wheels (Python 3.13 / manylinux x86_64) ──────────────────────
section "Pre-downloading wheels (Python ${WHEEL_PYTHON} / ${WHEEL_PLATFORMS[0]})"
rm -rf .flatpak-wheels
mkdir -p .flatpak-wheels

platform_args=()
for tag in "${WHEEL_PLATFORMS[@]}"; do platform_args+=(--platform "$tag"); done

run_with_spinner "Downloading wheels for $(grep -cE '^[^#[:space:]]' requirements.txt) requirements" -- \
    pip download --only-binary :all: \
        --python-version "${WHEEL_PYTHON}" --implementation cp \
        "${platform_args[@]}" \
        -q -d .flatpak-wheels -r requirements.txt

echo "  $(ls .flatpak-wheels/ | wc -l) distributions ready"

# ── Icons ─────────────────────────────────────────────────────────────────────
# The repo carries one master (assets/o7Debrief.png, 1254px square) and a
# Windows .ico; it has no hicolor size set, which is what a desktop needs to
# draw the app anywhere other than the window itself.  The set is derived here
# from that master rather than committed, so there is one source of truth for
# the artwork.  Every size is a DOWNSCALE of the master: nothing is ever
# resampled upwards, which would soften the artwork to fill a size it never had.
section "Generating hicolor icons from the master"
rm -rf packaging/icons
mkdir -p packaging/icons
python3 - <<'PYICONS'
from pathlib import Path

from PIL import Image

MASTER = Path("assets/o7Debrief.png")
OUT = Path("packaging/icons")
SIZES = (16, 32, 48, 64, 128, 256, 512)

master = Image.open(MASTER).convert("RGBA")
for size in SIZES:
    if size > master.width:
        raise SystemExit(
            f"master {MASTER} is {master.width}px, too small for a {size}px icon"
        )
    master.resize((size, size), Image.LANCZOS).save(OUT / f"o7debrief_{size}.png")
print(f"  {len(SIZES)} icon sizes written from {MASTER} ({master.width}px master)")
PYICONS

# ── Packaging helpers ─────────────────────────────────────────────────────────
section "Writing packaging helpers"
mkdir -p packaging

cat > packaging/o7debrief-launcher.sh <<LAUNCHER
#!/bin/sh
export LD_LIBRARY_PATH="/app/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export PYTHONPATH="/app/share/o7debrief:/app/lib/python${PYTHON_MM}/site-packages\${PYTHONPATH:+:\$PYTHONPATH}"
export QT_PLUGIN_PATH="/app/lib/python${PYTHON_MM}/site-packages/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="/app/lib/python${PYTHON_MM}/site-packages/PySide6/Qt/plugins/platforms"
if [ -n "\${WAYLAND_DISPLAY:-}" ] && [ -z "\${FORCE_X11:-}" ]; then
    export QT_QPA_PLATFORM=wayland
elif [ -n "\${DISPLAY:-}" ]; then
    export QT_QPA_PLATFORM=xcb
else
    export QT_QPA_PLATFORM=xcb
fi
exec python3 /app/share/o7debrief/main.py "\$@"
LAUNCHER
chmod +x packaging/o7debrief-launcher.sh

cat > "packaging/${APP_ID}.desktop" <<DESKTOP
[Desktop Entry]
Name=o7 Debrief
Comment=Turn the Elite Dangerous Player Journal into a Commander Mission Debrief
Exec=o7debrief
Icon=${APP_ID}
Terminal=false
Type=Application
Categories=Game;Utility;
DESKTOP

cat > "packaging/${APP_ID}.metainfo.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>${APP_ID}</id>
  <name>o7 Debrief</name>
  <summary>Commander Mission Debrief from the Elite Dangerous Player Journal</summary>
  <metadata_license>MIT</metadata_license>
  <project_license>LGPL-3.0-or-later</project_license>
  <description>
    <p>o7 Debrief watches the Elite Dangerous Player Journal while you play and
    produces a single self-contained Commander Mission Debrief when the session
    ends, opening it in your browser.  Every figure traces back to a real
    journal field; nothing is estimated, inferred or padded.</p>
  </description>
  <releases>
    <release version="${APP_VERSION}"/>
  </releases>
  <url type="homepage">https://ernster.dev/o7Debrief/</url>
</component>
XML

echo "  Packaging helpers ready."

# ── Manifest ──────────────────────────────────────────────────────────────────
section "Writing manifest ${MANIFEST}"

cat > "${MANIFEST}" <<YAML
app-id: ${APP_ID}
runtime: ${RUNTIME}
runtime-version: "${RUNTIME_VERSION}"
sdk: ${SDK}

command: o7debrief

build-options:
  strip: true
  no-debuginfo: true

finish-args:
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --device=dri
  # The update check is the app's one outbound call (GitHub's latest-release
  # endpoint); without network access the sandbox blocks it and every check
  # reports unreachable.
  - --share=network
  # The journal lives inside the game's Wine or Proton prefix under the user's
  # home, and the debrief is written to their Downloads folder, so home access
  # covers both.
  - --filesystem=home
  # Steam installed AS A FLATPAK keeps its Proton prefixes under ~/.var/app,
  # which flatpak deliberately excludes from --filesystem=home.  Without this
  # line o7 Debrief finds no journal at all on that very common setup and
  # reports no journal directory on a machine that plainly has one.  Read-only:
  # the app never writes to the journal.
  - --filesystem=~/.var/app/com.valvesoftware.Steam:ro
  # The "start when I sign in" setting writes an XDG autostart entry, which
  # lives outside the sandbox's own configuration.  Without this the toggle
  # fails silently and the background watcher never starts with the session.
  - --filesystem=xdg-config/autostart:create
  # Session-end notifications go through the desktop's notification service.
  - --talk-name=org.freedesktop.Notifications

modules:

  # ── Python dependencies (local wheels only, fully offline) ────────────────
  - name: python-deps
    buildsystem: simple
    build-commands:
      - python3 -m ensurepip --upgrade --default-pip
      - pip3 install --no-cache-dir --no-index --find-links wheels --prefix=/app
          -r requirements.txt
    sources:
      - type: dir
        path: .flatpak-wheels
        dest: wheels
      - type: file
        path: requirements.txt

  # ── o7 Debrief application source ─────────────────────────────────────────
  - name: o7debrief
    buildsystem: simple
    build-commands:
      - mkdir -p /app/share/o7debrief
      - cp main.py VERSION /app/share/o7debrief/
      - cp -r o7debrief /app/share/o7debrief/o7debrief
      - cp -r config /app/share/o7debrief/config
      - cp -r assets /app/share/o7debrief/assets
      # The Help > Licence dialog reads LICENSE from beside main.py, so it is
      # staged there as well as in the conventional licences location.
      - cp LICENSE /app/share/o7debrief/
      - install -Dm644 packaging/icons/o7debrief_16.png  /app/share/icons/hicolor/16x16/apps/${APP_ID}.png
      - install -Dm644 packaging/icons/o7debrief_32.png  /app/share/icons/hicolor/32x32/apps/${APP_ID}.png
      - install -Dm644 packaging/icons/o7debrief_48.png  /app/share/icons/hicolor/48x48/apps/${APP_ID}.png
      - install -Dm644 packaging/icons/o7debrief_64.png  /app/share/icons/hicolor/64x64/apps/${APP_ID}.png
      - install -Dm644 packaging/icons/o7debrief_128.png /app/share/icons/hicolor/128x128/apps/${APP_ID}.png
      - install -Dm644 packaging/icons/o7debrief_256.png /app/share/icons/hicolor/256x256/apps/${APP_ID}.png
      - install -Dm644 packaging/icons/o7debrief_512.png /app/share/icons/hicolor/512x512/apps/${APP_ID}.png
      - install -Dm755 packaging/o7debrief-launcher.sh /app/bin/o7debrief
      - install -Dm644 packaging/${APP_ID}.desktop /app/share/applications/${APP_ID}.desktop
      - install -Dm644 packaging/${APP_ID}.metainfo.xml /app/share/metainfo/${APP_ID}.metainfo.xml
      - install -Dm644 LICENSE /app/share/licenses/${APP_ID}/LICENSE
    sources:
      - type: file
        path: main.py
      - type: file
        path: VERSION
      - type: file
        path: LICENSE
      - type: dir
        path: o7debrief
        dest: o7debrief
      - type: dir
        path: config
        dest: config
      - type: dir
        path: assets
        dest: assets
      - type: dir
        path: packaging
        dest: packaging
YAML

echo "  Manifest written."

# ── Build ─────────────────────────────────────────────────────────────────────
section "Building Flatpak"
rm -rf "${BUILD_DIR}" "${REPO_DIR}"

flatpak-builder \
    --user \
    --install-deps-from=flathub \
    --install \
    --force-clean \
    --repo="${REPO_DIR}" \
    "${BUILD_DIR}" \
    "${MANIFEST}"

# ── Bundle (on by default; skip with --no-bundle) ─────────────────────────────
if [[ $MAKE_BUNDLE -eq 1 ]]; then
    section "Bundling to ${BUNDLE}"
    echo "  The spinner shows how much of ${BUNDLE} has been written."
    echo
    rm -f "${BUNDLE}"
    run_with_spinner "Writing ${BUNDLE}" --watch "${BUNDLE}" -- \
        flatpak build-bundle "${REPO_DIR}" "${BUNDLE}" "${APP_ID}"
    echo
    echo "${bold}Bundle: ${BUNDLE}  ($(du -sh "${BUNDLE}" | cut -f1))${reset}"
    echo
    echo "Install on another machine:"
    echo "  1. Copy ${BUNDLE} to the target machine"
    echo "  2. flatpak install --user ${BUNDLE}"
    echo "  3. flatpak run ${APP_ID}"
fi

echo
echo "${bold}Build complete.${reset}"
echo
echo "The app is already installed locally.  To manage it:"
echo
echo "  Run:        flatpak run ${APP_ID}"
echo "  Uninstall:  flatpak uninstall --user ${APP_ID}"
echo
echo "To have it watch the journal from sign-in, open Settings in the app and"
echo "tick the start-on-sign-in box.  That writes an XDG autostart entry running"
echo "'flatpak run ${APP_ID}'."
echo
if [[ $MAKE_BUNDLE -ne 1 ]]; then
    echo "Bundle skipped (--no-bundle).  Run without it to produce ${BUNDLE}."
    echo
fi
