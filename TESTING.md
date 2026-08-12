# Testing

The test strategy for o7 Debrief. The goal is a debrief that is reproducible and a codebase whose structure cannot quietly drift. The suite is organised so that the parts where correctness is pure logic are held to 100% coverage, while the parts whose correctness lives in talking to the real world (the Journal, the filesystem, a Qt event loop) are integration-tested instead. For the layers referenced here, see [ARCHITECTURE.md](ARCHITECTURE.md).

## The 100% gate and its scope

A hard coverage gate of 100% line and branch coverage applies to these packages:

- `o7debrief.domain`
- `o7debrief.application`
- `o7debrief.infrastructure.archive`
- `o7debrief.infrastructure.autostart`
- `o7debrief.infrastructure.clock`
- `o7debrief.infrastructure.sink`
- `o7debrief.infrastructure.update`
- `installer.ops`
- `installer.state`

The first two are the deterministic core: the reducer, the value objects, the `SessionDebrief` aggregate, the use cases and the ports. They are pure logic with injected dependencies, so every line and branch can be reached by a fast, deterministic test. Holding them at 100% is what makes "the same journal bytes produce the same debrief" a property the suite actually proves, not a hope.

The five infrastructure sub-packages are there because they already stood at 100% with no branch a test cannot reach. They are the adapters whose work is file and registry mechanics with no OS-specific discovery in them. The rest of infrastructure cannot join: measured as a whole the layer stands at 81%, with the shortfall concentrated in `journal/windows_paths.py` and `journal/paths.py`, which walk operating-system-specific locations a test on one machine cannot reach. Coverage carries a single fail-under, so gating the layer alongside those held at 100% would drag the one threshold down and quietly end the hard gate on the pure layers. That trade is recorded as open debt rather than taken.

The installer pair are the setup program's operations and its state model. They do the most privileged work in the product (registry writes, shortcut creation, per-user deployment, uninstall) and they are Qt-free, so they are gated rather than left unmeasured. Three seams make that possible without touching a real installation: commands are run through an injectable runner, the registry keys are a value that a test replaces with a scratch set and the per-user locations come from environment variables the suite redirects. No mocking library is used; the doubles are hand-written and live in `tests/installer/fakes.py`.

Four areas are deliberately excluded from the hard gate:

- The rest of `o7debrief.infrastructure` is integration-tested. Its correctness is in reading real Journal bytes, discovering the Journal directory, tailing from the right offset and writing files; that is exercised against sample journal fixtures, not measured by branch coverage of glue code.
- `o7debrief.ui` is exercised with light Qt tests under an offscreen platform. Its correctness is in wiring user actions to use cases, which is verified behaviourally rather than chased to 100%.
- The rest of the setup program is outside the measured set: `installer.ui` is its Qt client, `installer/app.py` is its composition root and `installer/cli.py` and `installer/constants.py` are the command line the registered `UninstallString` re-invokes and the names shared across the package. They are excluded on the same grounds as `o7debrief.ui` and `main.py`. One part of that client is tested anyway: `tests/installer/test_worker_shutdown.py` pins which thread the worker's results arrive on and that the thread is joined before the caller acts on them. A signal connected to a bare callable runs in the sending thread, so the teardown once asked the worker thread to wait for itself and the window hung. That is a defect no behavioural UI test would catch and no coverage figure would show, so it is pinned directly rather than left to the exclusion.
- `main.py`, the composition root, is wiring. It is covered by the application running and by the structural composition-root test, not by a coverage target.

Excluding these from the hard gate is a correctness decision, not a shortcut: a 100% target on IO and UI glue rewards mocking the real world, which is exactly where these layers must not be mocked.

## Test taxonomy

| Layer | Type | I/O | Notes |
| --- | --- | --- | --- |
| domain | Pure unit tests | None | The reducer, value objects and `SessionDebrief`, driven entirely in event-time. No clock, no files. |
| application | Unit tests with fakes | None | Use cases tested against fake implementations of the ports (journal source, clock, exporter, config). |
| infrastructure | Integration tests | Yes (temp) | Journal discovery, byte-offset tail and parse run against sample journal fixtures; exporters write to a temp directory. |
| ui | Light Qt tests | None | Real `QApplication` under `QT_QPA_PLATFORM=offscreen`; Qt is never mocked. No network. |
| installer | Unit tests with hand-written fakes | Yes (temp, HKCU scratch keys) | The setup program's operations and state, against a redirected profile and a unique registry key that the fixture removes afterwards, plus a thread-affinity guard on the Qt client's worker teardown. |
| structural | AST and source scans | File reads | Enforce the architectural invariants as tests so they cannot decay into convention. |

Alongside the per-layer split, a few behavioural guards pin the memory characteristics the app depends on (invariant I9): that a last-session debrief reads back only to the previous `Shutdown` rather than the whole journal, that the all-history debrief streams the journal one file at a time and that the live recorder retains only the current session. These live in the application and infrastructure suites next to the tests above.

### Structural tests

The structural suite under `tests/structural/` scans the source as an AST or as text and asserts the invariants from [ARCHITECTURE.md](ARCHITECTURE.md):

- `test_layering.py`: the dependency direction `ui -> application -> domain <- infrastructure` holds and the UI imports the application layer only.
- `test_domain_purity.py`: the domain imports no I/O, logging, `os`, `pathlib`, `threading` or wall-clock calls (`datetime.now()` / `date.today()`) and works in event-time only. Imports under `if TYPE_CHECKING:` are exempt.
- `test_loc_limits.py`: no module under `o7debrief/`, `installer/`, `tests/` or the repository root exceeds 400 lines. The setup program is in scope deliberately: it was one module of over a thousand lines that no rule could see. So is the root, which was in the same state: the composition root sat outside every scanned tree and was the largest module in the project. The exemptions there (the composition root and the delivery scripts) are named with a reason each; a companion test fails if an exemption names a file that no longer exists.
- `test_composition_root.py`: there is exactly one composition root and no module-level singletons or service locators elsewhere.
- `test_no_magic_numbers.py`: domain-specific values come from the TOML taxonomy or named constants, not inline literals.

## Running the suite and reading the result

Because the gate uses `--cov-fail-under=100`, a run has two ways to fail and only one of them is a test failure. Coverage falling below the threshold fails the run while every test still passes, so pytest's usual summary line can read `690 passed` on a run that exited non-zero. The line is real; it is just not the whole answer.

Reading the output needs the same care. The coverage table is printed after the test results and before that summary line, so any failure detail is well above both. Do not grep for `passed`, `failed` or `error` to decide the outcome: the table lists module paths, so a filename such as `errors.py` matches a grep for "error" on a completely clean run. Read the exit code.

```powershell
pytest
echo "EXIT=$LASTEXITCODE"
```

- `EXIT=0` means all tests passed and the 100% gate on every gated package was met.
- Any non-zero value means a failure. Check the line under the coverage table first: it says whether coverage reached the threshold. If it did, the cause is a test failure and that output sits above the table.

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

Coverage is configured in `pyproject.toml`. The gate is `--cov-fail-under=100` with branch coverage enabled, scoped via `--cov` to the packages listed above. Naming the measured packages explicitly is what keeps the gate honest: anything not named is simply not measured, so the ungated infrastructure, both UI layers and the two composition roots sit outside it by construction rather than by an omit rule that could silently widen. The omit list is kept to what a bare `pytest --cov` would otherwise pull in, for a reason learned the hard way: naming a layer there silenced it even when coverage was asked for it explicitly, so measuring infrastructure reported no data at all. Because the configuration lives in `pyproject.toml`, running `pytest` from the repository root applies the gate automatically; there is no separate flag to remember and no way to pass locally while silently dropping below the threshold.
