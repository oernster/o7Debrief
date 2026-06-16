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

Invariants I1 to I6 are the load-bearing structural rules and have dedicated tests. I7 and I8 are properties the structure makes possible and are pinned by the unit-test suite rather than by a single AST scan.

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

- A journal source port (path discovery, incremental byte-offset tail, parse) and a clock port for the few places that legitimately need wall-clock time (the crash-timeout safety net), kept out of the domain.
- An exporter port and a configuration port.
- The use cases: a live watch loop that debriefs the session at shutdown, a one-shot debrief of the last session and a one-shot debrief of the full history to date. Every path calls the same domain reducer.

A use case may itself be an immutable object holding its injected dependencies.

### infrastructure

Implements the application's ports against the real world; it is never imported by the domain or the application. It owns:

- Journal IO: Journal directory discovery, the incremental byte-offset tail that reads only new bytes and the parse skeleton. This IO is reused from the author's EDColonisationAsst, which already solves Journal path discovery and incremental tailing.
- Configuration loading from TOML via stdlib `tomllib`, supplying the event taxonomy and any tunable values so the domain stays free of magic numbers.
- Exporters: the Jinja2 HTML renderer (inlined CSS, zero JavaScript) and the Markdown renderer, plus file writing.

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

Live tray path: the watcher polls the active Journal file's modification time at a low frequency, tails new bytes from the last offset, feeds parsed events to the reducer and on a `Shutdown` event generates the debrief automatically. A crash-timeout acts as a safety net so a session that ends without a clean `Shutdown` still produces a report.

Cold one-shot path: "Debrief my last session" discovers the latest Journal, reads the slice from the last `LoadGame` to the end of the stream, runs the same reducer and renders the same `SessionDebrief`. It works even if o7 Debrief was not running during play.

Session isolation falls out of the slice rule: the current session is always "from the last `LoadGame` to the end of the stream", so events from an earlier session never enter the reduction.

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
| A desktop executable, not a local server. | The tool reads a local file and writes a local report; a server adds ports, lifecycle and attack surface for no user benefit. Local-first keeps the player's data on the player's machine. | A background HTTP service, a browser-based UI talking to localhost, any networked component. |
| Batch reporting, not live. | The value is reflective: a coherent end-of-session summary. A live feed is a different product (an overlay) with different constraints. | Real-time on-screen updates, an in-game overlay, continuous streaming of partial state. |
| TOML configuration for the event taxonomy. | The mapping from raw events to moments is data, not code; holding it in TOML (read with stdlib `tomllib`) keeps magic numbers and domain-specific mappings out of the logic and makes the taxonomy reviewable. | Hardcoded event-to-moment mappings and tuning constants scattered through the codebase. |
| Session isolation by last-`LoadGame` slice. | A session is unambiguously "the last `LoadGame` to the end of the stream". Defining it structurally means a previous session can never bleed into the current debrief. | Heuristic session boundaries, time-window guesses or accidental inclusion of a prior session's events. |

## Quality enforcement

The structure is held in place by the structural tests listed against the invariants, by a 100% line and branch coverage gate on `o7debrief.domain` and `o7debrief.application` and by constructor injection through a single composition root. Infrastructure and UI are integration-tested and deliberately excluded from the hard coverage gate, because their correctness lives in talking to the real Journal, the real filesystem and a real Qt event loop rather than in branch coverage of pure logic. The testing strategy is documented in [TESTING.md](TESTING.md) and the build-from-source workflow in [DEVELOPMENT-README.md](DEVELOPMENT-README.md).
