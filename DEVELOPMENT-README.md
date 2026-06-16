# Development

How to build and run o7 Debrief from source. o7 Debrief is a local-first Windows desktop application (Python 3.13 + PySide6) that produces a Commander Mission Debrief from the Elite Dangerous Journal. For what it is and what it is not, see [README.md](README.md); for how it is structured, see [ARCHITECTURE.md](ARCHITECTURE.md).

These instructions target Windows with PowerShell, which is the supported development platform for v1.

## Prerequisites

- Windows 10 or 11.
- Python 3.13, on `PATH` (confirm with `python --version`).
- Git, to clone the repository.

A working Elite Dangerous installation is useful for end-to-end checks because it produces real Journal files, but it is not required to run the tests: the suite drives the parsers from sample journal fixtures.

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
python -m pip install PySide6 Jinja2 pytest pytest-cov
```

`tomllib` is part of the Python 3.13 standard library, so configuration loading needs no extra package. PySide6 and Jinja2 are the runtime dependencies; pytest and pytest-cov are the development dependencies for the test suite and its coverage gate.

## Run the app from source

```powershell
python main.py
```

`main.py` is the single composition root: it wires the concrete infrastructure adapters into the application use cases and starts the PySide6 system-tray UI. o7 Debrief then sits in the tray, watches the active Journal and lets you generate a debrief on demand or automatically at session end.

## Run the tests and read the result

The project enforces 100% line and branch coverage on the domain and application layers. This changes how you read the result. A coverage-gated pytest run prints the coverage table last and emits no "N passed" summary line, so do not grep the output for `passed` or `failed`: substrings like `errors.py` in the coverage table are false matches. Trust the exit code.

```powershell
pytest
echo "EXIT=$LASTEXITCODE"
```

- `EXIT=0` means every test passed and the coverage gate was met.
- Any non-zero value means something failed; scroll up to the actual failures (not the coverage table) to see what.

If you need a plain pass/fail count while iterating, run without the coverage plugin:

```powershell
pytest --no-cov -q
```

The full strategy, taxonomy and coverage configuration are in [TESTING.md](TESTING.md).

## Build the executable

```powershell
python buildexe.py
```

`buildexe.py` drives Nuitka to produce a standalone Windows executable with the console disabled. Nuitka compiles the application ahead of time; the first build is slow, and a C compiler toolchain must be available (Nuitka will report what it needs if anything is missing). The result is a self-contained build that runs without a separate Python install.

## Build the installer

```powershell
python buildinstaller.py
```

`buildinstaller.py` packages the built executable into a Windows installer for distribution to end users.

## Project layout

```
o7debrief/
  domain/          Pure stdlib: journal value objects, conceptual-beat model,
                   the deterministic reducer, the SessionDebrief aggregate.
  application/     Use cases and ports (Protocols); domain + stdlib only.
  infrastructure/  Journal IO (discovery, byte-offset tail, parse), TOML config
                   loading, HTML (Jinja2) and Markdown exporters.
  ui/              PySide6 system tray and minimal windows; application layer only.
config/            TOML taxonomy mapping raw events to conceptual beats.
tests/
  ...              Unit, integration and structural tests mirroring the source.
  structural/      AST and source-scan boundary checks (layering, domain purity,
                   400-line limit, single composition root, no magic numbers).
main.py            The single composition root.
buildexe.py        Nuitka standalone build.
buildinstaller.py  Windows installer build.
```

The dependency direction is `ui -> application -> domain <- infrastructure`, enforced by the structural tests rather than by convention. Before adding code, read the invariants at the top of [ARCHITECTURE.md](ARCHITECTURE.md): they decide which layer a change belongs in.
