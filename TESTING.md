# Testing

The test strategy for o7 Debrief. The goal is a debrief that is reproducible and a codebase whose structure cannot quietly drift. The suite is organised so that the parts where correctness is pure logic are held to 100% coverage, while the parts whose correctness lives in talking to the real world (the Journal, the filesystem, a Qt event loop) are integration-tested instead. For the layers referenced here, see [ARCHITECTURE.md](ARCHITECTURE.md).

## The 100% gate and its scope

A hard coverage gate of 100% line and branch coverage applies to two layers:

- `o7debrief.domain`
- `o7debrief.application`

These are the deterministic core: the reducer, the value objects, the `SessionDebrief` aggregate, the use cases and the ports. They are pure logic with injected dependencies, so every line and branch can be reached by a fast, deterministic test. Holding them at 100% is what makes "the same journal bytes produce the same debrief" a property the suite actually proves, not a hope.

Three areas are deliberately excluded from the hard gate:

- `o7debrief.infrastructure` is integration-tested. Its correctness is in reading real Journal bytes, discovering the Journal directory, tailing from the right offset and writing files; that is exercised against sample journal fixtures, not measured by branch coverage of glue code.
- `o7debrief.ui` is exercised with light Qt tests under an offscreen platform. Its correctness is in wiring user actions to use cases, which is verified behaviourally rather than chased to 100%.
- `main.py`, the composition root, is wiring. It is covered by the application running and by the structural composition-root test, not by a coverage target.

Excluding these from the hard gate is a correctness decision, not a shortcut: a 100% target on IO and UI glue rewards mocking the real world, which is exactly where these layers must not be mocked.

## Test taxonomy

| Layer | Type | I/O | Notes |
| --- | --- | --- | --- |
| domain | Pure unit tests | None | The reducer, value objects and `SessionDebrief`, driven entirely in event-time. No clock, no files. |
| application | Unit tests with fakes | None | Use cases tested against fake implementations of the ports (journal source, clock, exporter, config). |
| infrastructure | Integration tests | Yes (temp) | Journal discovery, byte-offset tail and parse run against sample journal fixtures; exporters write to a temp directory. |
| ui | Light Qt tests | None | Real `QApplication` under `QT_QPA_PLATFORM=offscreen`; Qt is never mocked. No network. |
| structural | AST and source scans | File reads | Enforce the architectural invariants as tests so they cannot decay into convention. |

### Structural tests

The structural suite under `tests/structural/` scans the source as an AST or as text and asserts the invariants from [ARCHITECTURE.md](ARCHITECTURE.md):

- `test_layering.py`: the dependency direction `ui -> application -> domain <- infrastructure` holds, and the UI imports the application layer only.
- `test_domain_purity.py`: the domain imports no I/O, logging, `os`, `pathlib`, `threading` or wall-clock calls (`datetime.now()` / `date.today()`), and works in event-time only. Imports under `if TYPE_CHECKING:` are exempt.
- `test_loc_limits.py`: no module exceeds 400 lines.
- `test_composition_root.py`: there is exactly one composition root and no module-level singletons or service locators elsewhere.
- `test_no_magic_numbers.py`: domain-specific values come from the TOML taxonomy or named constants, not inline literals.

## Running the suite and reading the result

Because the gate uses `--cov-fail-under=100`, a normal run prints the coverage table last and emits no "N passed" summary line. Do not grep the output for `passed`, `failed` or `error`: filenames in the coverage table (for example `errors.py`) are false matches. Read the exit code.

```powershell
pytest
echo "EXIT=$LASTEXITCODE"
```

- `EXIT=0` means all tests passed and the 100% gate on domain and application was met.
- Any non-zero value means a failure; scroll past the coverage table to the actual failure output.

To run the UI tests headless, set the offscreen Qt platform first:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
pytest
echo "EXIT=$LASTEXITCODE"
```

For a quick pass/fail count while iterating, drop the coverage plugin so pytest prints its usual summary line:

```powershell
pytest --no-cov -q
```

To run one slice of the suite, point pytest at a path, for example the structural checks:

```powershell
pytest tests\structural
echo "EXIT=$LASTEXITCODE"
```

## How coverage is configured

Coverage is configured in `pyproject.toml`. The gate is `--cov-fail-under=100` with branch coverage enabled, scoped via `--cov` to `o7debrief.domain` and `o7debrief.application`. Infrastructure, UI and the composition root are omitted from the measured set, so the 100% requirement applies only to the deterministic core. Because the configuration lives in `pyproject.toml`, running `pytest` from the repository root applies the gate automatically; there is no separate flag to remember and no way to pass locally while silently dropping below the threshold.
