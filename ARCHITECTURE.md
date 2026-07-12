# Architecture

o7 Debrief is a local-first Windows desktop application that turns the Elite Dangerous player Journal into a Commander Mission Debrief. It is a desktop executable, not a web app and not a local server. This document states the structural invariants first, then the components, the dependency direction, the execution flow and the rationale behind the decisions that shaped the design.

The governing idea: a debrief is a deterministic function of the journal bytes for one session. Everything else (a tray, a one-shot command, an export format) is plumbing around that function. The architecture exists to keep that function pure, the data real and the layers honest.

## Invariants

Each invariant below is enforced by a structural test that scans the source as an AST or as text, so the rule cannot quietly rot into a convention. Where an invariant has no single test it is enforced by review and noted as such.

| # | Invariant | Enforced by |
| --- | --- | --- |
| I1 | Dependencies point inwards only: `ui -> application -> domain <- infrastructure`. No layer imports a layer it must not see. | [tests/structural/test_layering.py](tests/structural/test_layering.py) |
| I2 | The UI is a client of the application layer only. UI code never imports domain or infrastructure directly. | [tests/structural/test_layering.py](tests/structural/test_layering.py) |
| I3 | The domain is pure stdlib: no I/O, no logging, no `os`, no `pathlib`, no `threading` and no wall-clock reads (`datetime.now()` / `date.today()`). The domain works in event-time taken from journal fields. | [tests/structural/test_domain_purity.py](tests/structural/test_domain_purity.py) |
| I4 | No module exceeds 400 lines. Oversized modules are decomposed into helpers, not left to grow. | [tests/structural/test_loc_limits.py](tests/structural/test_loc_limits.py) |
| I5 | There is exactly one composition root. Dependencies are wired there by constructor injection; there are no module-level singletons or service locators elsewhere. | [tests/structural/test_composition_root.py](tests/structural/test_composition_root.py) |
| I6 | No magic numbers in logic. Domain-specific values (thresholds, day numbers, limits, the event taxonomy) come from the TOML configuration or named constants, never from inline literals. | [tests/structural/test_no_magic_numbers.py](tests/structural/test_no_magic_numbers.py) |
| I7 | Domain types are immutable: frozen dataclasses with `tuple[...]` collections, validated on construction. | [tests/structural/test_domain_purity.py](tests/structural/test_domain_purity.py) (paired with domain unit tests) |
| I8 | The two capture paths (live tray watcher and cold one-shot) feed one shared reducer, so the same journal bytes yield the same `SessionDebrief` regardless of trigger. | Domain and application unit tests (determinism), supported by I1 and I5 |
| I9 | Reads are bounded to the session they need, never the whole journal history. A last-session debrief reads back only to the previous `Shutdown`; the all-history debrief streams the journal one file at a time; the long-running tray recorder retains only the session in progress. | Application and infrastructure tests (the backward-scan, streaming and recorder-trim guards) |

Invariants I1 to I6 are the load-bearing structural rules and have dedicated tests. I7, I8 and I9 are properties the structure makes possible and are pinned by the test suite rather than by a single AST scan.

## Layers and components

The package is `o7debrief`, split into four layers plus a single composition root. The dependency arrows always point towards the domain.

```
        +----------------------------+
        |            ui              |   PySide6 tray + minimal windows
        +-------------+--------------+
                      | imports application only (I2)
                      v
        +----------------------------+
        |        application         |   use cases, ports, orchestration
        +-------------+--------------+
                      | imports domain + stdlib only
                      v
        +----------------------------+         +----------------------------+
        |          domain            | <------ |       infrastructure       |
        |  pure stdlib, event-time   | impl.   |  journal IO, config, files |
        +----------------------------+ ports   +----------------------------+
```

### domain

Pure Python on the standard library. Frozen dataclasses with `slots`, `tuple` collections and validation on construction. The domain holds:

- The journal-event value objects and the session-moment model that raw events roll up into.
- The deterministic reducer that folds a sequence of parsed events into the moments for one session, working entirely in event-time read from journal timestamps.
- The `SessionDebrief` aggregate: the finished, render-ready view of a session, including rank changes (tier-ups now, percentages deferred), built only from real journal fields.

The domain reads no clock, opens no file and logs nothing. Time comes in as data on the events. This is what makes a debrief reproducible.

### application

The domain plus stdlib only; it never imports infrastructure or UI. It defines the ports (Protocols) that infrastructure implements and the use cases that orchestrate a debrief:

- A journal source port that reads only what a debrief needs: path discovery, an incremental byte-offset tail for the live watcher, a bounded read of the latest session (back only to the previous `Shutdown`) and a per-file streaming read for the all-history debrief, so no path loads the whole journal into memory. A clock port covers the few places that legitimately need wall-clock time (the crash-timeout safety net), kept out of the domain.
- An exporter port, a configuration port and a release-source port that supplies the latest published version for the opt-in update check.
- The use cases: a live watch loop that debriefs the session at shutdown, a one-shot debrief of the last session and a one-shot debrief of the full history to date. The all-history use case folds the journal file by file, keeping only the moments, the state-bearing events and the window endpoints rather than every event at once. Every path calls the same domain reducer.
- An update service that compares the running version against the latest release through a pure version comparison and reports whether a newer one exists, so the ui can point the player at the download. It is the only application service that touches the network, and only through the injected release-source port.

A use case may itself be an immutable object holding its injected dependencies.

### infrastructure

Implements the application's ports against the real world; it is never imported by the domain or the application. It owns:

- Journal IO: Journal directory discovery, the incremental byte-offset tail that reads only new bytes, a newest-first backward read that stops as soon as it has bracketed the latest session, a per-file batch iterator for streaming the whole history and the parse skeleton. The tail and discovery are reused from the author's EDColonisationAsst, which already solves Journal path discovery and incremental tailing.
- Configuration loading from TOML via stdlib `tomllib`, supplying the event taxonomy and any tunable values so the domain stays free of magic numbers.
- Exporters: the Jinja2 HTML renderer (inlined CSS, zero JavaScript) and the Markdown renderer, plus file writing. Each timeline row renders its activity (domain) glyph with the control mode shown as a compact tag, so a row reads as what the Commander did rather than which control mode held it; a death row additionally names who destroyed the Commander, or the cause (a self-destruct), a ship-launched-vehicle row (the Nomad vessel or a fighter) names the vehicle type, a bounty row names the destroyed ship, and a completed-mission row names the mission (an Operation carries a readable title) with its faction and any Merc Coins it paid, all read from the moment detail by a dedicated `timeline_text` builder in the application layer. The session log is ordered most recent first.
- A GitHub release source for the update check: a single short, best-effort HTTPS GET built on the standard-library `urllib` (no third-party HTTP dependency), returning the latest release tag or None on any failure.

### ui

PySide6, the client of the application layer only. It owns the system-tray icon and menu, the minimal windows and the user actions (debrief the last session, debrief the full history to date, choose export format and open the home screen). It holds no domain logic; it calls use cases and displays their results.

### Composition root

A single `main.py` constructs the concrete infrastructure adapters and injects them into the application use cases, then hands those to the UI. This is the only place wiring happens (I5). There are no module-level singletons.

## Execution flow

The same core path serves both capture modes. The difference is only where the journal bytes come from and what triggers the render.

```
journal bytes  ->  parse (infrastructure)  ->  reducer (domain)
                                                   |
                                                   v
                                            SessionDebrief (domain)
                                                   |
                                  +----------------+----------------+
                                  v                                 v
                          HTML exporter                     Markdown exporter
                        (Jinja2, inlined CSS,             (Discord / Reddit
                         zero JavaScript)                   paste format)
```

Live tray path: the watcher polls the active Journal at a low frequency, tails new bytes from the last offset and feeds parsed events to the reducer, retaining only the session in progress so a tray left running for days stays bounded in memory. On a `Shutdown` event it generates the debrief automatically; a crash-timeout acts as a safety net so a session that ends without a clean `Shutdown` still produces a report.

Cold one-shot path: "Debrief my last session" reads the newest Journal files backwards, stopping as soon as it has seen enough `Shutdown` events to bracket the latest run (typically the newest file or two), runs the same reducer and renders the same `SessionDebrief`. It never reads the whole history and works even if o7 Debrief was not running during play. "Debrief my history to date" does cover every event but streams the journal one file at a time, folding each file into a bounded summary rather than loading it all at once.

Session isolation is by `Shutdown` bracketing: the latest session is the run ending at the last `Shutdown` (or the end of the log when the game closed without one), starting just after the previous `Shutdown`. Every `LoadGame` within that run, including those a return to the main menu fires, stays in the session, so an earlier session never enters the reduction.

Rank handling reflects what the journal can actually tell us. A `Promotion` (a tier-up) is reported in the session it happens. Fractional rank percentages are only snapshotted by the journal at startup, so they are finalised at the next launch; only ranks that changed are shown, never a full unchanged ladder.

## Design-decision rationale

### Core feature and output decisions

| # | Decision | Why | What it rules out |
| --- | --- | --- | --- |
| 1 | Ship both capture paths in v1 (live tray watcher and cold one-shot). | The two paths cover the two real situations: app running during play and app not running but you still want a debrief. One shared reducer keeps them consistent. | A v1 that only worked if you remembered to start the app first or only worked as a manual after-the-fact tool. |
| 2 | HTML and Markdown in v1, with a configurable default format overridable per export. | HTML is the canonical, self-contained, portable artefact; Markdown is what you paste into Discord or Reddit. A default keeps the common case one click; per-export override keeps it flexible. | Locking users into a single format or forcing a format choice on every single export. |
| 3 | Real data only: every number traces to a journal field. | Trust is the product. A debrief that estimates or guesses is worse than no debrief because the reader cannot tell which figures are real. | Derived or interpolated statistics that look authoritative but cannot be verified against the journal. |
| 4 | Pure-Python Windows executable now; a Linux port later if there is demand. | The audience is on Windows; a Nuitka standalone exe ships without asking users to install Python. Pure Python keeps the Linux port a packaging exercise, not a rewrite. | A cross-platform v1 that delays the Windows release the audience actually wants or a native rewrite per platform. |
| 5 | Strict UI boundary: the UI imports the application layer only. | It keeps the UI swappable (tray today, more later) and keeps domain logic out of widgets, which is where logic goes to become untestable. | A UI that reaches into the domain or infrastructure and quietly becomes the place business rules live. |
| 6 | Ranks as tier-ups-now plus percentages-next-launch, showing only changed ranks. | It matches what the journal records: promotions are events but progress percentages are only snapshotted at startup. Reporting them this way is honest rather than fabricated. | Inventing a mid-session percentage the journal never recorded or padding the report with unchanged ranks. |

### Keystone decisions

| Decision | Why | What it rules out |
| --- | --- | --- |
| A desktop executable, not a local server. | The tool reads a local file and writes a local report; a server adds ports, lifecycle and attack surface for no user benefit. Local-first keeps the player's data on the player's machine. | A background HTTP service, a browser-based UI talking to localhost, any inbound network surface. The one exception is the opt-in update check: a single outbound GET the player triggers by hand, which never downloads or runs anything and fails silently. |
| Batch reporting, not live. | The value is reflective: a coherent end-of-session summary. A live feed is a different product (an overlay) with different constraints. | Real-time on-screen updates, an in-game overlay, continuous streaming of partial state. |
| TOML configuration for the event taxonomy. | The mapping from raw events to moments is data, not code; holding it in TOML (read with stdlib `tomllib`) keeps magic numbers and domain-specific mappings out of the logic and makes the taxonomy reviewable. | Hardcoded event-to-moment mappings and tuning constants scattered through the codebase. |
| A data-driven where-filter on a moment rule. | Some journal events are shared across many subjects and only become a specific moment when one payload field carries a distinguishing token. The Nomad reuses `LaunchFighter` to deploy (a Nomad deployment only when its `Loadout` is one of the vessel variants) and `ModuleBuy` covers the Vessel Hangar (a hangar purchase only when the item name contains `fighterbay`). A rule may name a `where_field` and a list of `where_contains` tokens, matching when the field contains any of them, so the discriminator lives in the taxonomy rather than as an event-name-specific branch in code. One event can carry several candidate rules (the Nomad and every fighter share `LaunchFighter`); the reducer uses the first whose filter matches, so taxonomy order sets precedence. The phase tracker reads the same Nomad-deployment discriminator from the taxonomy rather than hardcoding loadout strings. Adding a variant or correcting a game-side rename is a one-line config edit. | Per-event conditional logic in the reducer, and hardcoded module, loadout or item identifiers in the domain. |
| Merc Coins as a separate currency channel from credits. | Operations pay a Merc Coins reward alongside credits, and coins are not credits. A moment carries a distinct `coins_delta` beside its `credits_delta`, summed into the Missions rollup's own `coin_rewards` total, so coins never fold into the session's net-credits figure. The coin field is read from a taxonomy-named `coins_field` because the reward is new game content absent from the published journal schema; if the live journal names it differently, only the taxonomy value changes. | Adding coins into the credit total (which would silently corrupt net credits), and hardcoding the coin journal field name in the domain. |
| Session isolation by `Shutdown` bracketing. | A session is one game run, bounded by `Shutdown` events; the latest is the run ending at the last `Shutdown`. Anchoring on `Shutdown` rather than `LoadGame` keeps a run that returned to the main menu (which fires a fresh `LoadGame`) whole. Defining it structurally means a previous session can never bleed into the current debrief. | Heuristic session boundaries, time-window guesses and shrinking a run to its final leg by anchoring on `LoadGame`. |
| Reads bounded to the session, not the journal history. | A debrief is a function of one session's bytes, so reading the entire journal to produce one was waste that grew without limit as a Commander's logs piled up. The last-session read walks back only to the previous `Shutdown`, the all-history read streams file by file and the tray recorder keeps only the current session. | Loading the whole journal history into memory for a debrief; an always-on tray whose memory grows with uptime. |

## Quality enforcement

The structure is held in place by the structural tests listed against the invariants, by a 100% line and branch coverage gate on `o7debrief.domain` and `o7debrief.application` and by constructor injection through a single composition root. Infrastructure and UI are integration-tested and deliberately excluded from the hard coverage gate, because their correctness lives in talking to the real Journal, the real filesystem and a real Qt event loop rather than in branch coverage of pure logic. The testing strategy is documented in [TESTING.md](TESTING.md) and the build-from-source workflow in [DEVELOPMENT-README.md](DEVELOPMENT-README.md).
