# o7Debrief: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `o7debrief` package, the composition root, the taxonomy configuration, the bespoke installer and the delivery scripts) read against `ARCHITECTURE.md`, `TESTING.md` and the tests under `tests/structural/`.

This is the most rigorously enforced project in the portfolio. `tests/structural/` holds five separate suites: layering, domain purity (including a ban on reading the clock), a composition-root whitelist, a magic-numbers test that exists nowhere else in the account and a 400-line cap over `o7debrief/`, `installer/` and `tests/`. The domain and application layers are gated at 100% branch coverage, as are the setup program's operations and state model. The list below is short because there is not much left.

---

## 1. The Merc Coins journal field name is an assumption; a wrong guess reads as zero

`config/debrief_taxonomy.toml:264` sets `coins_field = "MercCoins"`, naming the key the Operations reward is read from in the Elite Dangerous journal. That name was inferred, not confirmed against a real completed-Operation journal entry.

`o7debrief/domain/aggregation/moment_factory.py` reads it as designed:

```python
raw = event.get(rule.coins_field)
if isinstance(raw, int) and not isinstance(raw, bool):
    return Credits(raw)
return Credits.zero()
```

The docstring is explicit that this "yields zero rather than a guessed value" and as a domain rule that is exactly right: a missing or non-integer field must not fabricate a number.

The consequence is the item. If the real journal key is spelled differently, every Operation silently reports 0 Merc Coins. There is no error, no warning and no test that can catch it, because the tests supply the field under the name the config assumes. The whole feature would be quietly inert and would look like a game that pays no coins.

This is a verification gap rather than a defect and it closes with evidence rather than with code: run a real completed Operation, read the journal line and confirm the key. Two things are worth doing regardless of the outcome:

- Add a note beside the config value recording when and against what it was confirmed.
- Consider surfacing a one-time diagnostic when a rule names a `coins_field` that is absent from an event it otherwise matched. That converts a silent zero into something observable without weakening the domain rule.

## 2. `main.py` is 514 lines and is the one module the size rule cannot see

`tests/structural/test_loc_limits.py` walks `o7debrief/`, `installer/` and `tests/` and fails anything over 400 lines. `main.py` is at repository root, so it is outside that scope; at 514 lines it is the largest Python file in the project.

Its own docstring explains why it is long and the explanation is a good one: it is the single place permitted to import infrastructure, it constructs every adapter explicitly and it deliberately avoids module-level singletons and scattered literals. A composition root that wires a dozen ports honestly will be long; the alternative (hiding the wiring in a container) is worse and is banned here for good reason.

So the item is not "shorten it". It is that the one file exempt from the rule is exempt by accident of location rather than by a stated decision. Two options, either acceptable:

- Extend `test_loc_limits.py` over root modules and add `main.py` to an explicit exemption list with the reason written beside it, in the way Calendifier's `_LEGACY_OVER_LIMIT` and NarrateX's `_BUILD_SCRIPTS` do.
- Or split the wiring into small `build_*` helper functions in a `wiring` module that `main.py` calls, keeping the composition-root whitelist test satisfied.

The first is honest and cheap. The second is tidier and risks obscuring the linear flow the docstring values.

## 3. Infrastructure and UI are tested but not gated

`addopts` gates `o7debrief.domain`, `o7debrief.application`, `installer.ops` and `installer.state` at 100% branch coverage. So two of the application's four layers are outside it.

Infrastructure is not ungated because it is untested: `tests/infrastructure/` holds twelve test modules covering the journal source, the config provider, both renderers, the archive, the sink, both stores, the release source, the icons, Windows autostart and an end-to-end test. That is thorough. It simply does not count toward the failing threshold, so coverage there can decay without anything reporting it.

The journal source and `windows_paths.py` are the parts worth bringing inside. They are the boundary with the outside world, which is precisely where item 1's failure mode lives. Adding `--cov=o7debrief.infrastructure` at whatever level the existing tests already achieve (then raising it from there) costs nothing today and stops the drift.

The UI omission is correct and should stay.

## 4. The coverage omit list has drifted out of step with the gate

`[tool.coverage.run].omit` in `pyproject.toml` still names `o7debrief/main.py`, a path that does not exist: the composition root is `main.py` at the repository root. The entry has no effect either way, because `addopts` scopes `--cov` to four named packages and nothing outside them is measured at all, so the omit list is doing no work for the application layers it lists.

It is worth a minute because a config line that names a file that is not there invites the wrong conclusion, namely that exclusion is what keeps the composition root out of the gate. It is not: package scoping is. The cheap fix is to delete the stale entry and the two now-redundant layer entries, leaving a comment that says package scoping is the mechanism. Correcting the path instead would at least make the list true. The `shibokensupport`, `signature_bootstrap.py`, `pyscript` and `tests/*` entries are load-bearing and must stay, because a bare `pytest --cov` would otherwise pull them in.

---

## Looks like debt, not worth touching

- `tests/domain/aggregation/test_moment_factory.py` (399), `o7debrief/ui/tray/tray_controller.py` (396) and `tests/application/test_debrief_presenter.py` (394). All three are inside the 381 to 399 danger band, so each wants taking to 350 when next touched. The size test covers `o7debrief/` and `tests/`, so it will catch them the moment they grow.
- The `tools/` scripts (`capture_home_dialog.py`, `capture_tray_menu.py`, `generate_example_report.py`, `make_icon.py`) printing to stdout. Development instruments, correctly separated from the package.
- The very large number of single-name `__all__` declarations across `application/ports/` and `application/dto/`. Repetitive and correct: one port or DTO per module, each exporting exactly one name.
- `schema_version="1.0.0"` appearing as a literal in a test fixture. Test data, not a version source.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **`tests/structural/test_no_magic_numbers.py`.** No other project in the portfolio has one. For an application that aggregates credits, ranks and rewards, a test that forbids unexplained numeric literals in the domain is the single most appropriate invariant available. Do not weaken it for convenience.
- **`test_domain_never_reads_the_clock()`.** The domain assembles moments from journal timestamps; letting it read the wall clock would make debriefs non-reproducible. Load-bearing.
- **The eleven ports in `application/ports/` with one Protocol each.** It looks like ceremony for a desktop app. It is what lets the domain and application layers hold a 100% branch gate with no I/O and it is why the infrastructure tests can use real temporary files rather than mocks.
- **`_coins_from()` returning zero rather than raising on a missing field.** Correct domain behaviour and stated in its docstring. Item 1 is about verifying the field name and making a mismatch observable at the boundary, not about changing this rule.
- **`config/debrief_taxonomy.toml` holding the event taxonomy and its text templates as data.** The rules the application applies are configuration, not code. This is why adding a new journal event does not mean editing the domain.
- **`VERSION` at root with `o7debrief/__init__.py` exposing `__version__`.** Single source of truth, correctly implemented, with no literal anywhere else in the tree.
- **The two `# noqa: BLE001` handlers in `journal/paths.py` and `journal/windows_paths.py`.** Each has a written reason ("a stubbed environ may misbehave", "any WinAPI failure falls back below"). This is the house style done correctly.
- **The three `# pragma: no cover` handlers in `installer/ops/paths.py`.** They sit inside a package held at 100%, which normally deserves suspicion. Each one guards an `OSError` from `Path.resolve()` that no test can provoke on Windows and each carries a written explanation of why it is unreachable and why the fallback is the safe direction. Deleting them to satisfy the gate would remove a correct defence; faking a failure to cover them would test the fake.
- **The `# noqa: E402` markers on the imports in `tools/`.** Those scripts put the repository root on `sys.path` (and set the Qt scaling environment) before importing from the package, so the imports must follow the bootstrap. The markers record that. `ruff check --isolated` reports all twenty-seven of them as unused, because it runs with E402 disabled and no project configuration to enable it; `--fix` would then strip them and re-sort the imports. Under `flake8`, which is the linter the project configures, they are load-bearing and the tree is clean. This is a false positive from a tool the project does not use, not debt.
