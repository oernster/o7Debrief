# o7Debrief: Technical Debt

A standing reference to the project's outstanding technical debt. It records what is still open, weighs whether each item is worth doing and gives the rationale. Every item is a behaviour-preserving internal concern: nothing here proposes reverting a feature or changing any UI or UX behaviour. Scope is the whole repository (the `o7debrief` package, the composition root, the taxonomy configuration, the bespoke installer and the delivery scripts) read against `ARCHITECTURE.md`, `TESTING.md` and the tests under `tests/structural/`.

This is the most rigorously enforced project in the portfolio. `tests/structural/` holds seven separate suites: layering, domain purity (including a ban on reading the clock), a composition-root whitelist, a magic-numbers test that exists nowhere else in the account, a 400-line cap over `o7debrief/`, `installer/`, `tests/` and the repository root, a desktop-identity check pinning the Linux application id across the build script and the composition root; and a prose-style check enforcing the em-dash and comma rules across every file that carries prose. The domain and application layers are gated at 100% branch coverage, as are the setup program's operations and state model. The list below is short because there is not much left.

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

Infrastructure as a whole measures **86%** branch coverage on Windows and the figure moves with the platform it is measured on, since each operating system leaves the other's discovery module unreachable. The shortfall is concentrated and explicable: `journal/windows_paths.py` is at 0% and `journal/paths.py` at 34%, both being OS-specific path discovery that a test on one machine cannot walk; `line_parser.py` (70%) and `event_mapper.py` (75%) carry malformed-input branches.

The blocker is that coverage.py has a single `fail-under`. Gating a layer measured at 86% alongside layers held at 100% would drag the one threshold down to match it and quietly end the hard gate on the pure layers, which is a far worse outcome than the drift it would prevent. So the options are:

- Raise the remaining sub-packages to 100% with fakes for the OS-specific discovery, then add them to `addopts`. Honest; the work is mostly in `journal/paths.py`.
- Or run a second, separately floored coverage pass for infrastructure and wire it into the verification routine. That keeps the pure gate intact but adds a second command to remember, which is the kind of remembered step this project deliberately converts into rules.

The UI omission is correct and should stay.

## 3. The Flatpak builds and runs; parts of it are still unproven

`build_flatpak.sh`, `cleanup_flatpak.sh` and `LinuxAutostart` were written on a Windows machine with no Linux, no `flatpak-builder` and no Elite Dangerous under Proton. That is no longer the whole story: the Flatpak has now been built and run on a real Ubuntu machine. What that settled and what it did not is worth stating exactly, because the gap between the two is what is left of this item.

Settled by running it:

- The manifest builds, the wheels resolve against the runtime's Python and the app installs and launches. That was the largest single unknown and it is gone.
- The tray was broken and is fixed. A Qt tray icon on Linux is not drawn into a panel: it is published over D-Bus as a StatusNotifierItem for the desktop's watcher to draw. The manifest named only the notification service, so the sandbox blocked the watcher, `isSystemTrayAvailable()` answered False and the app reported no tray on a desktop that had one. The prediction below had been that stock GNOME lacks a host; on Ubuntu there is a host and the sandbox was refusing it. Granting `--talk-name=org.kde.StatusNotifierWatcher` restores the icon, confirmed by running with that grant added. Ownership of the item's own bus name was tried too and proved unnecessary, so the narrower grant is what ships.
- Tray presence is no longer assumed either way. That fix settled one desktop; it did not make a tray something the app may count on, so availability is now asked of the running desktop rather than inferred from the platform, then asked repeatedly over a grace period rather than once, because an autostart launch precedes the panel that would host the icon. Where none appears the home window opens, so the no-tray case is a supported path rather than a warning on a stream nobody reads. Both branches were run: the tray branch on the Ubuntu session, the fallback branch under the offscreen platform, which reports no tray and therefore exercises it for real.

Verified before that and still only that:

- Both scripts pass `bash -n`.
- The icon-generation block was run against the real 1254px master and produces all seven sizes.
- `LinuxAutostart` is unit-tested at 100% branch coverage against a temporary directory.
- The summon route was run for real on Windows across two processes: a second launch leaves the marker, exits cleanly and the running instance consumes it and opens its window. What that does not prove is the sandbox part of it, below.

Still unverified: whether the sandbox can actually read a Proton prefix, whether the autostart entry survives a real session start and whether `webbrowser.open` reaches a host browser through the portal from inside the sandbox. Those need a machine with the game installed rather than another build.

Three things remain most likely to be wrong:

- **The Steam-as-Flatpak journal path.** `--filesystem=home` does not cover `~/.var/app`, which is why the manifest carries a second explicit `--filesystem=~/.var/app/com.valvesoftware.Steam:ro`. If that line is wrong or insufficient, discovery fails on a machine that plainly has a journal; the report then says no journal directory rather than saying it was not allowed to look.
- **Opening the debrief.** The Windows path opens the file with `webbrowser`; inside the sandbox that has to travel through the portal to a browser on the host. It is the whole point of the Linux release and it is entirely untested.
- **The summon route's sandbox assumption.** Launching the app again opens the home window rather than exiting in silence. It is no longer the only route to a tray-less desktop, since the app now opens that window itself when no tray appears; it remains the route back after the window is closed. It rests on one thing this machine cannot check: inside a flatpak each instance gets its own `XDG_RUNTIME_DIR`, so the lock file and the summon marker are placed in `$XDG_RUNTIME_DIR/app/$FLATPAK_ID`, the directory flatpak shares between instances of one application. If that is wrong or not mounted as expected, two launches take two locks: a second tray appears and the summon marker is never seen. It is written from the documented sandbox layout and verified only against a temporary directory standing in for it.

What closes the rest is a Linux machine with Elite Dangerous installed under Proton, not further reading. Until a debrief has been generated from a real journal there and opened in a browser, the end-to-end Linux path is built but not proven and no document should claim otherwise.

Two things have moved since that was written and the wording above is narrower than it was because of them. The Flatpak bundle is now published as a release asset rather than being something a reader had to build, so the documents and the site offer it and say plainly which part of it is unproven, rather than declining to mention a file that is plainly there for download. What that does not change is the substance of this item: the install path is proven and the play path is not, so nothing anywhere claims the second.

---

## Looks like debt, not worth touching

- `tests/domain/aggregation/test_moment_factory.py` (399). It sits at the top of the 381 to 399 danger band, so it wants taking to 350 when next touched. The size test covers `o7debrief/`, `installer/`, `tests/` and the repository root, so it will catch it the moment it grows.
- The `tools/` scripts (`capture_home_dialog.py`, `capture_installer_window.py`, `capture_tray_menu.py`, `generate_example_report.py`, `make_icon.py`) printing to stdout. Development instruments, correctly separated from the package.
- The very large number of single-name `__all__` declarations across `application/ports/` and `application/dto/`. Repetitive and correct: one concern per module. Most export exactly one name; the handful that export more export a cohesive cluster that has no meaning apart (a bundle and the files in it, a page and its tabs, a result and the port that returns it, the view and its sub-views), which is the same rule rather than an exception to it.
- `schema_version="1.0.0"` appearing as a literal in a test fixture. Test data, not a version source.
- `[humanise.words]` holding one entry per token part, so a part cannot mean different things on different modules. `fast` is Bi-Weave on a shield generator and Enhanced Performance on a thruster; mapping it would be right in one report and wrong in the other, so it is left out and reads as "Fast" on both. That is imprecise about each and false about neither, which is the right side to err on here. Module-aware entries are the fix if the imprecision ever matters; the cost is a second lookup layer for two or three words.

## Not debt (do not "fix" these)

These look like candidates but are correct as they stand; changing them would regress or add cost for nothing.

- **`tests/structural/test_no_magic_numbers.py`.** No other project in the portfolio has one. For an application that aggregates credits, ranks and rewards, a test that forbids unexplained numeric literals in the domain is the single most appropriate invariant available. Do not weaken it for convenience.
- **`test_domain_never_reads_the_clock()`.** The domain assembles moments from journal timestamps; letting it read the wall clock would make debriefs non-reproducible. Load-bearing.
- **The twelve ports in `application/ports/` with one Protocol each.** It looks like ceremony for a desktop app. It is what lets the domain and application layers hold a 100% branch gate with no I/O and it is why the infrastructure tests can use real temporary files rather than mocks.
- **`_coins_from()` returning zero rather than raising on a missing field.** Correct domain behaviour and stated in its docstring. Item 1 is about verifying the field name, not about changing this rule. Making a mismatch observable is done: `application/services/field_diagnostics.py` reports an unread currency or magnitude field as a notice in the report itself.
- **`config/debrief_taxonomy.toml` holding the event taxonomy and its text templates as data.** The rules the application applies are configuration, not code. This is why adding a new journal event does not mean editing the domain.
- **`VERSION` at root with `o7debrief/__init__.py` exposing `__version__`.** Single source of truth, correctly implemented, with no version literal anywhere in the source. Two files in the site state a version and neither is hand-maintained: `docs/index.html` carries a delimited token that `stamp_version.py` overwrites and `docs/example-report.html` is a rendered report that `refresh_example_report.py` regenerates. Both build scripts run both, so neither can drift from `VERSION`.
- **The three `# noqa: BLE001` handlers in `journal/paths.py` and `journal/windows_paths.py`.** Each has a written reason ("a stubbed environ may misbehave", "any WinAPI failure falls back below", "freeing failures are non-fatal"). Two more sit in `installer/ui/worker.py` and `ui/tray/update_check.py` on the same terms. This is the house style done correctly.
- **The three `# pragma: no cover` handlers in `installer/ops/paths.py`.** They sit inside a package held at 100%, which normally deserves suspicion. Each one guards an `OSError` from `Path.resolve()` that no test can provoke on Windows and each carries a written explanation of why it is unreachable and why the fallback is the safe direction. Deleting them to satisfy the gate would remove a correct defence; faking a failure to cover them would test the fake.
- **The four `RUF100` per-file ignores in `pyproject.toml`.** The `tools/` scripts put the repository root on `sys.path` (and set the Qt scaling environment) before importing from the package, so those imports must follow the bootstrap; `tests/installer/test_worker_shutdown.py` does the same after a `pytest.importorskip`. Each such import carries a `# noqa: E402`. ruff does not enable E402 by default, so it once read all thirty-eight of those markers as unused directives and `--fix` would have stripped them and re-sorted the imports they protect. Enabling E402 in the ruff configuration settled thirty of them. The rest are a real disagreement rather than a gap: ruff's E402 tolerates a few statements before an import that flake8 does not, so it calls those seven markers unnecessary, plus one `# noqa: SLF001` on a capture script's deliberate private read that ruff would only accept if SLF001 were enabled across the tree, where it would fire on every test that reaches into the object it is testing. Removing the markers makes flake8 report fifteen E402 errors, which is how the disagreement was settled rather than assumed. flake8 is the linter the project enforces, so the markers stay and the four files tell ruff not to call them unused. Both linters are clean on the whole tree.
