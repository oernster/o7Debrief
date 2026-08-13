# Development

How to build and run o7 Debrief from source. o7 Debrief is a local-first Windows desktop application (Python 3.13 + PySide6) that produces a Commander Mission Debrief from the Elite Dangerous Journal. For what it is and what it is not, see [README.md](README.md); for how it is structured, see [ARCHITECTURE.md](ARCHITECTURE.md).

These instructions target Windows with PowerShell, which is the platform every release is built and tested on. Building and running from source on Linux has its own section below, since almost nothing above transfers unchanged.

## Prerequisites

- Windows 10 or 11.
- Python 3.13, on `PATH` (confirm with `python --version`).
- Git, to clone the repository.

A working Elite Dangerous installation is useful for end-to-end checks because it produces real Journal files but it is not required to run the tests: the suite drives the parsers from sample journal fixtures.

## Create and activate the virtual environment

From the repository root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, allow it for the current user once with `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again. Your prompt shows `(venv)` when the environment is active.

## Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` pulls in `requirements.txt` as well, so this one command covers everything: the runtime dependencies (PySide6 and Jinja2), the test runner, the coverage plugin, the formatter, both linters, Nuitka for the Windows build and Pillow, which the Flatpak build uses to derive the icon set. To run the app without any of the development tooling, install `requirements.txt` alone.

`tomllib` is part of the Python 3.13 standard library, so configuration loading needs no extra package.

## Run the app from source

```powershell
python main.py
```

`main.py` is the single composition root: it wires the concrete infrastructure adapters into the application use cases and starts the PySide6 UI. o7 Debrief then runs in the background, in the system tray where the desktop draws one and behind its home window where it does not, watches the active Journal and lets you generate a debrief on demand or automatically at session end.

## Run the tests and read the result

The project enforces 100% line and branch coverage on the domain and application layers, on the five infrastructure sub-packages that can reach it and on the setup program's operations and state model. This changes how you read the result, because a run can fail with every test passing: coverage below the threshold fails it on its own. Do not grep the output for `passed`, `failed` or `error` either, since the coverage table lists module paths and a filename such as `errors.py` matches "error" on a clean run. Trust the exit code.

```powershell
pytest
echo "EXIT=$LASTEXITCODE"
```

- `EXIT=0` means every test passed and the coverage gate was met.
- Any non-zero value means something failed. The line just under the coverage table says whether coverage reached the threshold; if it did, scroll further up to the test failures themselves.

If you need a plain pass/fail count while iterating, run without the coverage plugin:

```powershell
pytest --no-cov -q
```

The full strategy, taxonomy and coverage configuration are in [TESTING.md](TESTING.md).

## Format and lint

The tree is kept formatted with black at a line length of 88 and clean under flake8, both configured in `pyproject.toml` and `.flake8`:

```powershell
black .
flake8
echo "EXIT=$LASTEXITCODE"
```

One exception is deliberate. The scripts under `tools/` add the repository root to `sys.path` (and set the Qt scaling environment) before importing from the package, so their imports must stay below that bootstrap; each carries a `# noqa: E402` marker to say so. `tests/installer/test_worker_shutdown.py` does the same thing for the same reason. Do not let an import sorter move or strip those markers, because reordering the imports breaks the scripts.

`ruff` is configured in `pyproject.toml` and the tree is clean under it too:

```powershell
ruff check .
echo "EXIT=$LASTEXITCODE"
```

The configuration exists because of those markers. ruff does not enable E402 by default, so out of the box it read all thirty-eight deliberate suppressions in the tree as unused directives and `ruff --fix` would have stripped them and re-sorted the imports they protect. The fix was to enable E402, which is the rule flake8 already enforces, so a clean run of either linter now means the same thing. Four files still carry a `RUF100` per-file ignore, because ruff's E402 tolerates a few statements before an import that flake8 does not (setting `QT_SCALE_FACTOR`, calling `pytest.importorskip`) and so calls those particular markers unnecessary. flake8 disagrees and flake8 is what the project enforces: remove them and it reports fifteen E402 errors. Take `ruff --fix` nowhere near those four files.

## Build the executable

```powershell
python buildexe.py
```

`buildexe.py` drives Nuitka to produce a standalone Windows executable with the console disabled. Nuitka compiles the application ahead of time; the first build is slow and a C compiler toolchain must be available (Nuitka will report what it needs if anything is missing). The result is a self-contained build that runs without a separate Python install.

## Build the installer

```powershell
python buildinstaller.py
```

`buildinstaller.py` packages the built executable into a Windows installer for distribution to end users. It compiles `installer_main.py` at the repository root, which is the entry point into the `installer` package. The entry script sits at the root rather than inside the package because a script is compiled with its own directory on the module search path, so compiling `installer/app.py` directly would leave the `installer.*` imports unresolvable.

To run the setup program from source without building it:

```powershell
python installer_main.py
```

## Build and run from source on Linux

This section names what o7 Debrief needs rather than which package provides it. The answer differs on every distribution; on some of them the usual answer is actively wrong, so a list of `apt install` lines would be a confident way to mislead most readers. Nothing here has been run on anything but Ubuntu; the requirements are read from the project, the distribution-specific parts are yours to map.

### What it actually needs

- **Python 3.13 or newer.** The floor is real rather than cautious: configuration is read with the standard library's `tomllib`.
- **Two packages**, `PySide6` (6.6 or newer, below 7) and `Jinja2`. Everything else the app uses is the standard library, so those two are the whole of `requirements.txt`.
- **A session to draw in**, Wayland or X11. The PySide6 wheel carries Qt itself but links against the graphics libraries your system provides.
- Nothing else. No service, no daemon, no root, no system-wide install, no compiler.

### The usual route

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python main.py
```

To run the app rather than develop it, install `requirements.txt` alone. That is two packages instead of the full toolchain, leaving out Nuitka, which only drives the Windows build and is of no use here. On a system where wheels are the difficulty that is also two chances to fail instead of several.

### When the wheel is the wrong answer

`pip install PySide6` fetches a manylinux wheel; a manylinux wheel assumes a conventional filesystem: an interpreter and loader at fixed paths, shared libraries reachable on a global search path. A distribution that does not work that way will install the wheel perfectly happily and then fail to import it, which reads as a broken package rather than as a mismatched assumption. NixOS is the clear case and it is not the only one.

The answer there is either to take Qt for Python from the distribution rather than from pip or to run inside an environment that presents the conventional layout. Which of those is right is a question about your distribution rather than about this project, so this document does not pretend to answer it. Nothing in o7 Debrief cares where PySide6 came from.

Two commands separate the possible problems:

```bash
python -c "import PySide6.QtWidgets; print('Qt imports')"
```

```bash
QT_DEBUG_PLUGINS=1 python main.py
```

The first tells a Python-level import failure from a Qt-level one. The second makes Qt name every platform plugin it tried and why it rejected each, which is what to read when the import succeeds and no window ever appears.

### It will not start without a journal

Discovery is not optional. o7 Debrief resolves the journal directory before it builds anything; when it finds none it says so and stops with exit code 1: a message on stderr and a dialog carrying the locations it tried in its details. That is the normal state of any machine you are only building on, so expect it on a first run and read it as a statement about the machine rather than as a fault in the build.

You can satisfy discovery without owning the game, because `WINEPREFIX` is honoured and searched at the path Windows would use:

```bash
export WINEPREFIX=/tmp/o7debrief-prefix
mkdir -p "$WINEPREFIX/drive_c/users/$USER/Saved Games/Frontier Developments/Elite Dangerous"
python main.py
```

The directory can stay empty. The app starts, finds no sessions and says so, which is enough to exercise the interface, the settings, the update check and the summon route. `STEAM_COMPAT_DATA_PATH` is honoured the same way for a Proton layout; the Steam locations searched are listed in `o7debrief/infrastructure/journal/paths.py` rather than duplicated here.

### The tray and what to do without one

A Qt tray icon on Linux is not drawn into a panel by the app. It is published over D-Bus as a StatusNotifierItem and the desktop's own watcher draws it, so whether an icon appears is a fact about your session rather than about o7 Debrief. Where no watcher is running the app says so on startup and carries on working: the journal is still watched and debriefs are still written.

The route in when there is no tray is to launch o7 Debrief again. The second launch hands the request to the copy already running and closes; that copy opens its home window, which holds every operation the tray menu does. That is also what makes a desktop launcher entry useful on a session with no tray at all.

### There is no standalone Linux binary

`buildexe.py` is Nuitka driving a Windows build, with Windows PE metadata and a Windows icon flag, so it is Windows-only and there is no Linux equivalent. Linux has two supported shapes instead: running from source as above and the Flatpak below.

## Build the Flatpak

This one runs on Linux, from a checkout with the virtual environment created:

```bash
./build_flatpak.sh
```

The script writes its own manifest, launcher, desktop entry and metainfo rather than committing them, derives the whole icon set from the single master PNG at `assets/o7Debrief.png`, pre-downloads the wheels on the host so the sandboxed build needs no network, then installs the app and produces `o7debrief.flatpak`. `./cleanup_flatpak.sh` reverses it: it removes the build trees, the wheels, the generated manifest and packaging files and the bundle; it uninstalls the app as well, since a cleanup that left the one thing actually installed on the machine would not be one. Pass `--keep-installed` to clear the artefacts and keep the app. It touches nothing the other two delivery paths produced, so the Nuitka build outputs are left alone.

The bundle it produces is what each release publishes as `o7debrief.flatpak`. It has been built, installed and run on Ubuntu. What has not been proven is producing a debrief from a real journal inside a Proton prefix, so [TECH_DEBT.md](TECH_DEBT.md) item 4 records exactly what has and has not been verified and is worth reading before you trust it.

## Stamp the version into the site

```powershell
python stamp_version.py
```

`VERSION` at the repository root is the single source of truth. The runtime and `pyproject.toml` read it directly; the GitHub Pages site under `docs/` cannot, so each page carries a delimited `<!--VERSION-->` token that this script overwrites from `VERSION`. It is idempotent and prints the files it touched. Both `buildexe.py` and `buildinstaller.py` call it at the start of a build, so a packaged release cannot ship a site showing the wrong version.

## Project layout

```
o7debrief/
  domain/          Pure stdlib: journal value objects, session-moment model,
                   the deterministic reducer, the SessionDebrief aggregate.
  application/     Use cases and ports (Protocols); domain + stdlib only.
  infrastructure/  Journal IO (discovery, byte-offset tail, a bounded latest-session
                   read, per-file streaming and parse), TOML config loading,
                   HTML (Jinja2), HTML-bundle and Markdown exporters, the
                   single-file sink and the bundle sink.
  ui/              PySide6 system tray and minimal windows; application layer only.
installer/         The setup program, split so the privileged work is measurable.
  ops/             Payload extraction, paths, shortcuts, process control and the
                   install, repair and uninstall sequences, each reporting phase
                   and progress through an injected callback. No Qt.
  state/           The HKCU registrations, version comparison and the state model.
  shared/          Resource resolution and crash logging.
  ui/              The themed window, its dialogs and the worker thread that runs
                   a sequence off the interface thread; the only Qt client.
  cli.py           The command line the registered UninstallString re-invokes.
  constants.py     The names shared across the package.
  app.py           The setup program's composition root.
config/            TOML taxonomy mapping raw events to moments.
docs/              The GitHub Pages site, stamped with the version from VERSION.
tools/             Development instruments (icon generation, screenshot capture,
                   the example report). Not part of the shipped package.
tests/
  ...              Unit, integration and structural tests mirroring the source.
  installer/       The setup program's operations and state, against scratch
                   registry keys and a redirected profile.
  structural/      AST and source-scan boundary checks (layering, domain purity,
                   400-line limit including the repository root, single
                   composition root, no magic numbers, Linux desktop identity).
main.py            The single composition root.
installer_main.py  Entry point for the setup program.
buildexe.py        Nuitka standalone build.
buildinstaller.py  Windows installer build.
build_flatpak.sh   Linux Flatpak build; writes its own manifest and packaging files.
cleanup_flatpak.sh Removes only what the Flatpak build produced.
stamp_version.py   Stamps VERSION into the docs/ site.
VERSION            The single source of truth for the version.
```

The dependency direction is `ui -> application -> domain <- infrastructure`, enforced by the structural tests rather than by convention. Before adding code, read the invariants at the top of [ARCHITECTURE.md](ARCHITECTURE.md): they decide which layer a change belongs in.
