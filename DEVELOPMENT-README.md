# Development

How to build and run o7 Debrief from source. o7 Debrief is a local-first Windows desktop application (Python 3.13 + PySide6) that produces a Commander Mission Debrief from the Elite Dangerous Journal. For what it is and what it is not, see [README.md](README.md); for how it is structured, see [ARCHITECTURE.md](ARCHITECTURE.md).

These instructions target Windows with PowerShell, which is the supported development platform for v1.

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

`requirements-dev.txt` pulls in `requirements.txt` as well, so this one command covers everything: the runtime dependencies (PySide6 and Jinja2), the test runner, the coverage plugin, the formatter, the linter and Nuitka for the builds. To run the app without any of the development tooling, install `requirements.txt` alone.

`tomllib` is part of the Python 3.13 standard library, so configuration loading needs no extra package.

## Run the app from source

```powershell
python main.py
```

`main.py` is the single composition root: it wires the concrete infrastructure adapters into the application use cases and starts the PySide6 system-tray UI. o7 Debrief then sits in the tray, watches the active Journal and lets you generate a debrief on demand or automatically at session end.

## Run the tests and read the result

The project enforces 100% line and branch coverage on the domain and application layers and on the setup program's operations and state model. This changes how you read the result, because a run can fail with every test passing: coverage below the threshold fails it on its own. Do not grep the output for `passed`, `failed` or `error` either, since the coverage table lists module paths and a filename such as `errors.py` matches "error" on a clean run. Trust the exit code.

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

One exception is deliberate. The scripts under `tools/` add the repository root to `sys.path` (and set the Qt scaling environment) before importing from the package, so their imports must stay below that bootstrap; each carries a `# noqa: E402` marker to say so. Do not let an import sorter move or strip them, because reordering those imports breaks the scripts.

This matters if you reach for `ruff`. The project has no ruff configuration, so `ruff check --isolated` runs with E402 disabled, decides every one of those markers is unused and offers to remove them and re-sort the imports. Under `flake8`, which is what the project actually configures, the same markers are load-bearing and the tree is clean. Take `ruff --fix` nowhere near `tools/`.

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

## Project layout

```
o7debrief/
  domain/          Pure stdlib: journal value objects, session-moment model,
                   the deterministic reducer, the SessionDebrief aggregate.
  application/     Use cases and ports (Protocols); domain + stdlib only.
  infrastructure/  Journal IO (discovery, byte-offset tail, a bounded latest-session
                   read, per-file streaming and parse), TOML config loading,
                   HTML (Jinja2) and Markdown exporters.
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
tools/             Development instruments (icon generation, screenshot capture,
                   the example report). Not part of the shipped package.
tests/
  ...              Unit, integration and structural tests mirroring the source.
  installer/       The setup program's operations and state, against scratch
                   registry keys and a redirected profile.
  structural/      AST and source-scan boundary checks (layering, domain purity,
                   400-line limit, single composition root, no magic numbers).
main.py            The single composition root.
installer_main.py  Entry point for the setup program.
buildexe.py        Nuitka standalone build.
buildinstaller.py  Windows installer build.
VERSION            The single source of truth for the version.
```

The dependency direction is `ui -> application -> domain <- infrastructure`, enforced by the structural tests rather than by convention. Before adding code, read the invariants at the top of [ARCHITECTURE.md](ARCHITECTURE.md): they decide which layer a change belongs in.
