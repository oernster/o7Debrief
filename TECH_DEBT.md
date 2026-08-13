# o7Debrief: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `o7debrief` package, the composition root, the taxonomy configuration, the bespoke installer and the delivery scripts) read against `ARCHITECTURE.md`, `TESTING.md` and the tests under `tests/structural/`.

This is the most rigorously enforced project in the portfolio. `tests/structural/` holds five separate suites: layering, domain purity (including a ban on reading the clock), a composition-root whitelist, a magic-numbers test that exists nowhere else in the account and a 400-line cap over `o7debrief/`, `installer/` and `tests/`. The domain and application layers are gated at 100% branch coverage, as are the setup program's operations and state model. The list below is short because there is not much left.

---

## 1. The Merc Coins journal field name is an assumption; a wrong guess reads as zero

`config/debrief_taxonomy.toml` sets `coins_field = "MercCoins"` on the `MissionCompleted` rule, naming the key the Operations reward is read from in the Elite Dangerous journal. That name was inferred, not confirmed against a real completed-Operation journal entry.

`o7debrief/domain/aggregation/moment_factory.py` reads it as designed:

```python
raw = event.get(rule.coins_field)
if isinstance(raw, int) and not isinstance(raw, bool):
    return Credits(raw)
return Credits.zero()
```

The docstring is explicit that this "yields zero rather than a guessed value" and as a domain rule that is exactly right: a missing or non-integer field must not fabricate a number.

The consequence is the item. If the real journal key is spelled differently, every Operation silently reports 0 Merc Coins. There is no error, no warning and no test that can catch it, because the tests supply the field under the name the config assumes. The whole feature would be quietly inert and would look like a game that pays no coins.

### Published sources cannot settle it; the assumption may be wrong twice over

The name was searched for in the sources that would document it. None do.

- **Frontier's own Player Journal Manual is abandoned.** The newest published revision is v32, whose changelog reads "Changes up to Odyssey Update 5 (July 2021)". No official journal documentation exists for anything since 2021, so the Operations update has none of any kind.
- **The best community-maintained schema shows no such field.** [Elite Dangerous Journal Schemas](https://jixxed.github.io/ed-journal-schemas/) lists `MissionCompleted` in full: timestamp, event, Faction, Name, LocalisedName, MissionID, Commodity, Commodity_Localised, Count, Reward, PermitsAwarded, CommodityReward, MaterialsReward, FactionEffects, Influence, ReputationTrend, Reputation, Donation, Donated, TargetFaction, DestinationSystem, DestinationStation, Target, Target_Localised, DestinationSettlement, TargetType, TargetType_Localised, KillCount, NewDestinationSystem, NewDestinationStation. No coin field, no merc field, no currency but credits.
- **Community sources confirm the currency, not its representation.** Operations pay Merc Coin, capped at 9999 with a 1000 weekly allowance. Nothing describes how it is journalled.

The consequence is worse than a possibly misspelled key. A schema that tracks the journal actively shows `MissionCompleted` unchanged, so the reward may ride a different event entirely or may not be journalled at all. The assumption is therefore open on two axes: the field name and the event that carries it.

### It cannot be closed from this machine

The local journals hold **zero** `MissionCompleted` events across all 77 files. Every occurrence of "Coin" in them is another commander's chat message. So the mission path as a whole, not only the coins field, has never been exercised against real data here; no amount of reading the existing journals can confirm anything.

This is a verification gap rather than a defect and it closes with evidence rather than with code: complete a real Operation, read the journal line and confirm both the event and the key. Two things are worth doing regardless of the outcome:

- Add a note beside the config value recording what it was confirmed against.
- Surface a one-time diagnostic when a rule names a `coins_field` that is absent from an event it otherwise matched. That converts a silent zero into something observable without weakening the domain rule. It is now the more valuable half: it would report which event actually carries the reward the first time one is paid.

## 2. Most of infrastructure is tested but cannot join the hard gate

`addopts` gates `o7debrief.domain`, `o7debrief.application`, five infrastructure sub-packages (`archive`, `autostart`, `clock`, `sink`, `update`), `installer.ops` and `installer.state` at 100% branch coverage. Those five joined because they already stood at 100% with no unreachable branch. The other five (`config`, `journal`, `preferences`, `rank`, `render`) did not; the reason is structural rather than a lack of effort.

Infrastructure as a whole measures **82%** branch coverage. The shortfall is concentrated and explicable: `journal/windows_paths.py` is at 0% and `journal/paths.py` at 34%, both being OS-specific path discovery that a test on one machine cannot walk; `line_parser.py` (70%) and `event_mapper.py` (75%) carry malformed-input branches.

The blocker is that coverage.py has a single `fail-under`. Gating a layer measured at 81% alongside layers held at 100% would drag the one threshold down to match it and quietly end the hard gate on the pure layers, which is a far worse outcome than the drift it would prevent. So the options are:

- Raise the remaining sub-packages to 100% with fakes for the OS-specific discovery, then add them to `addopts`. Honest; the work is mostly in `journal/paths.py`.
- Or run a second, separately floored coverage pass for infrastructure and wire it into the verification routine. That keeps the pure gate intact but adds a second command to remember, which is the kind of remembered step this project deliberately converts into rules.

The UI omission is correct and should stay.

## 3. House prose style is unenforced; breaches sit in the tree

The house style forbids em dashes outright and forbids a comma directly before or after a coordinating conjunction (`and`, `or`, `but`), which rules out the Oxford comma. Nothing checks either rule, so both drift wherever prose is written: docstrings, comments, Markdown and the taxonomy's own commentary.

A sweep of the tree finds **87** comma breaches across **57 files** and no em dashes. The count is real rather than estimated: it comes from a detector that spans newlines. That matters because the common case is a comma ending one line and the conjunction opening the next; a single-line search misses every one of those and then reports a clean tree.

Nothing here is a correctness problem; it is house style, applied unevenly. Two ways to close it:

- Sweep the remaining files in one pass. Cheap in thought but wide in diff, touching prose across every layer at once.
- Add a structural test alongside the em-dash rule so the tree cannot drift again, then clear the backlog it reports. That converts a remembered habit into a rule, which is what this project does with every other invariant. It is only worth doing once the backlog is cleared, since a guard that fails on day one gets skipped.

The second is the better shape and should follow the first rather than lead it. Note the detector requirement above in either case: a naive single-line regex reports a false all-clear on this very tree.

## 4. The Flatpak has never been built or run

`build_flatpak.sh`, `cleanup_flatpak.sh` and `LinuxAutostart` were written on a Windows machine with no Linux, no `flatpak-builder` and no Elite Dangerous under Proton. What has actually been verified is narrow and worth stating exactly, because the gap between it and "it works" is the item:

- Both scripts pass `bash -n`.
- The icon-generation block was run against the real 1254px master and produces all seven sizes.
- `LinuxAutostart` is unit-tested at 100% branch coverage against a temporary directory.

Everything that makes it a working Linux release is unverified: whether the manifest builds, whether the wheel platform tags resolve against the runtime's Python, whether the sandbox can actually read a Proton prefix, whether the autostart entry survives a real session start, plus whether `webbrowser.open` reaches a host browser through the portal from inside the sandbox.

Three things are most likely to be wrong on first run:

- **The Steam-as-Flatpak journal path.** `--filesystem=home` does not cover `~/.var/app`, which is why the manifest carries a second explicit `--filesystem=~/.var/app/com.valvesoftware.Steam:ro`. If that line is wrong or insufficient, discovery fails on a machine that plainly has a journal; the report then says no journal directory rather than saying it was not allowed to look.
- **Opening the debrief.** The Windows path opens the file with `webbrowser`; inside the sandbox that has to travel through the portal to a browser on the host. It is the whole point of the Linux release and it is entirely untested.
- **The tray icon.** `QSystemTrayIcon` needs a StatusNotifierItem host. Ubuntu ships one; a stock GNOME session does not, so the icon simply will not appear there. The background watch and the browser-on-exit do not depend on it, so the product still works; the tray menu is unreachable on those desktops though, which nothing currently says to the user.

This closes by building and running it on a real Ubuntu machine, not by further reading. Until then the Linux support is written but not shipped; no document should claim otherwise.

---

## Looks like debt, not worth touching

- `tests/domain/aggregation/test_moment_factory.py` (399). It sits at the top of the 381 to 399 danger band, so it wants taking to 350 when next touched. The size test covers `o7debrief/`, `installer/`, `tests/` and the repository root, so it will catch it the moment it grows.
- The `tools/` scripts (`capture_home_dialog.py`, `capture_tray_menu.py`, `generate_example_report.py`, `make_icon.py`) printing to stdout. Development instruments, correctly separated from the package.
- The very large number of single-name `__all__` declarations across `application/ports/` and `application/dto/`. Repetitive and correct: one port or DTO per module, each exporting exactly one name.
- `schema_version="1.0.0"` appearing as a literal in a test fixture. Test data, not a version source.
- `[humanise.words]` holding one entry per token part, so a part cannot mean different things on different modules. `fast` is Bi-Weave on a shield generator and Enhanced Performance on a thruster; mapping it would be right in one report and wrong in the other, so it is left out and reads as "Fast" on both. That is imprecise about each and false about neither, which is the right side to err on here. Module-aware entries are the fix if the imprecision ever matters; the cost is a second lookup layer for two or three words.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **`tests/structural/test_no_magic_numbers.py`.** No other project in the portfolio has one. For an application that aggregates credits, ranks and rewards, a test that forbids unexplained numeric literals in the domain is the single most appropriate invariant available. Do not weaken it for convenience.
- **`test_domain_never_reads_the_clock()`.** The domain assembles moments from journal timestamps; letting it read the wall clock would make debriefs non-reproducible. Load-bearing.
- **The eleven ports in `application/ports/` with one Protocol each.** It looks like ceremony for a desktop app. It is what lets the domain and application layers hold a 100% branch gate with no I/O and it is why the infrastructure tests can use real temporary files rather than mocks.
- **`_coins_from()` returning zero rather than raising on a missing field.** Correct domain behaviour and stated in its docstring. Item 1 is about verifying the field name, not about changing this rule. Making a mismatch observable is done: `application/services/field_diagnostics.py` reports an unread currency or magnitude field as a notice in the report itself.
- **`config/debrief_taxonomy.toml` holding the event taxonomy and its text templates as data.** The rules the application applies are configuration, not code. This is why adding a new journal event does not mean editing the domain.
- **`VERSION` at root with `o7debrief/__init__.py` exposing `__version__`.** Single source of truth, correctly implemented, with no literal anywhere else in the tree.
- **The two `# noqa: BLE001` handlers in `journal/paths.py` and `journal/windows_paths.py`.** Each has a written reason ("a stubbed environ may misbehave", "any WinAPI failure falls back below"). This is the house style done correctly.
- **The three `# pragma: no cover` handlers in `installer/ops/paths.py`.** They sit inside a package held at 100%, which normally deserves suspicion. Each one guards an `OSError` from `Path.resolve()` that no test can provoke on Windows and each carries a written explanation of why it is unreachable and why the fallback is the safe direction. Deleting them to satisfy the gate would remove a correct defence; faking a failure to cover them would test the fake.
- **The `# noqa: E402` markers on the imports in `tools/`.** Those scripts put the repository root on `sys.path` (and set the Qt scaling environment) before importing from the package, so the imports must follow the bootstrap. The markers record that. `ruff check --isolated` reports all thirty-four of them as unused, because it runs with E402 disabled and no project configuration to enable it; `--fix` would then strip them and re-sort the imports. Under `flake8`, which is the linter the project configures, they are load-bearing and the tree is clean. This is a false positive from a tool the project does not use, not debt.
