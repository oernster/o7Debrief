# Decisions and trade-offs

The deliberate choices o7 Debrief rests on: what was chosen, what was given up
for it and why. Each entry is the decision as the product makes it today.
The detail behind each one, with the invariants and the tests that hold it,
lives in [ARCHITECTURE.md](ARCHITECTURE.md) and [TESTING.md](TESTING.md);
[TECH_DEBT.md](TECH_DEBT.md) holds what is still open and what only looks like
debt.

## The product as a whole

### A desktop program, not a local server

o7 Debrief reads a local file and writes a local report. It runs as a tray
program on the player's own machine and opens no port.

- **Rather than:** a background web service with a browser interface talking
  to localhost.
- **Gains:** no ports, no service lifecycle and no inbound surface to defend;
  the player's journal stays on the player's machine.
- **Costs:** the report is read in a browser the program does not control.

### A report after the session, not an overlay

The value is a coherent summary once the flying is done. Nothing is drawn on
screen during play.

- **Rather than:** a live feed or an in-game overlay.
- **Gains:** one well-defined input (a finished session) and one output; no
  timing constraints from the game.
- **Costs:** nothing is shown while the session is under way.

### Every figure traces to a journal field

Nothing in the report is estimated, interpolated or padded. A figure is
printed only when the journal stated it.

- **Rather than:** derived statistics that look authoritative but cannot be
  checked against the journal.
- **Gains:** a reader can trust every number on the page; a doubtful one can
  be found in the player's own files.
- **Costs:** some questions a player would like answered (a closing balance,
  a mid-session rank percentage) are left unanswered because the journal does
  not state them.

### Pure Python on Qt for Python

The application is Python with PySide6 for the tray and windows and Jinja2
for the report. Everything else is the standard library.

- **Rather than:** a native rewrite per platform.
- **Gains:** the Linux port cost a packaging script and one autostart adapter,
  with no change to the domain, the application layer or the reducer.
- **Costs:** a larger runtime than a native binary; packaging needs a
  compiler on Windows and a Flatpak on Linux.

### Free, with a donation link

There is no paid tier, no licence key and no feature held back. The README
and the website carry a donation button.

- **Rather than:** a paid product or a paid tier.
- **Gains:** nothing in the program has to check what the player paid for.
- **Costs:** none recorded.

## Privacy and the network

### One outbound call and nothing inbound

The update check is the only network request the program makes. It is a
single short request to GitHub's latest-release address, with a five second
timeout, built on the standard library. Nothing listens for a connection.

- **Rather than:** a third-party HTTP library; any other route out.
- **Gains:** "local first" is a property of the code rather than a promise;
  no dependency is added for one request.
- **Costs:** the Flatpak still needs the network grant for that one call.

### Update checks: shortly after launch, then daily, quiet unless there is news

An automatic check runs three seconds after launch and once a day. It says
nothing unless a newer release exists and ignores a version the player chose
to skip. The check on the home screen and in the tray menu ignores the skip
and reports every outcome. GitHub's endpoint returns only published releases,
so a tag pushed during development never prompts.

- **Rather than:** a check only on request; one that reports every outcome.
- **Gains:** updates are found without nagging; a failed automatic check is
  silent.
- **Costs:** one unprompted request a day; there is no setting to turn the
  automatic check off.

### Downloads go through the browser

Choosing Download in the update prompt opens the platform's installer address
(or the releases page) in the default browser. The program never fetches or
runs an installer itself.

- **Rather than:** downloading and running the update in the program.
- **Gains:** nothing is downloaded or run without the player choosing it; no
  second network route.
- **Costs:** the player runs the installer by hand.

### A second launch summons the first through a file

Launching o7 Debrief while it is running leaves a marker file beside the
single-instance lock and exits. The running copy looks for the marker four
times a second and opens its home window. The marker carries no instruction;
its presence is the whole message.

- **Rather than:** a local socket the running copy listens on.
- **Gains:** no inbound surface and no port to own; a second process can ask
  to be seen but can direct nothing. A stale marker left by a crash is
  discarded at the next start, so nobody gets a window they did not ask for.
- **Costs:** a small poll that runs for the life of the process.

### The Flatpak asks for the narrowest grants that work

The sandbox may talk to the desktop's tray watcher by name and to the
notification service. It reads a Steam installed as a Flatpak read-only and
may create the autostart entry. Owning the tray item's own bus name was tried
on Ubuntu and proved unnecessary.

- **Rather than:** the whole session bus, which owning that bus name would
  have forced since Flatpak cannot express its pattern.
- **Gains:** the tray icon appears with one named grant.
- **Costs:** each new desktop integration needs its own grant and a run on a
  real machine to prove it.

## Reading the journal

### The journal is read, never written

Every reader opens the journal for reading only. Inside the Flatpak the Steam
Flatpak's folder is granted read-only.

- **Rather than:** any write path near the game's files.
- **Gains:** o7 Debrief cannot damage what the game records.
- **Costs:** none recorded.

### A session is bracketed by Shutdown

The latest session is the run ending at the last Shutdown, starting just
after the one before. A run with no Shutdown at the end (the game crashed)
runs to the end of the log. Every LoadGame inside the run stays in it.

- **Rather than:** anchoring on LoadGame, which the game fires on every return
  to the main menu and so would shrink a run to its final leg; time-window
  guesses.
- **Gains:** a previous session can never bleed into the current one; a run
  that touched the menu stays whole.
- **Costs:** none recorded.

### Two ways in, one reducer

The live watcher and the on-demand debriefs (the last session and the whole
history) feed the same domain reducer.

- **Rather than:** a debrief only if the program was running during play; a
  manual tool only.
- **Gains:** the same journal bytes give the same debrief whatever triggered
  it; a debrief works even if o7 Debrief was not running while the player
  flew.
- **Costs:** none recorded.

### Reads bounded to the session

A last-session debrief reads journal files newest first and stops at the
second Shutdown. The history report streams the journal one file at a time.
The live recorder keeps only the session in progress.

- **Rather than:** loading the whole journal history for every debrief.
- **Gains:** memory and time stay bounded however many years of logs the
  player has; a watcher left running for days does not grow.
- **Costs:** the history report still reads every file, by design.

### A timer reads what was appended

The watcher reads the newest journal file from the last byte offset every
five seconds, carrying a half-written line over to the next read.

- **Rather than:** filesystem notifications through a third-party library.
- **Gains:** no extra dependency; a single code path on every platform; the
  program stays close to idle.
- **Costs:** up to five seconds between the game writing an event and the
  program seeing it.

### Automatic debriefs fire once per Shutdown, never on start-up

The first look at the journal only records the session already there. After
that, each new Shutdown triggers one debrief, identified by its own
timestamp.

- **Rather than:** debriefing whatever finished session the program finds
  when it starts.
- **Gains:** starting with Windows never reopens an old debrief; a session is
  debriefed exactly once.
- **Costs:** a session that ends in a crash, with no Shutdown, gets no
  automatic debrief; "Debrief my last session" still covers it.

### Ranks: promotions now, percentages at the next launch

A promotion is reported in the session it happens. Rank percentages are
written to the journal only at start-up, so they are compared against a saved
snapshot and settle at the next launch. Only ranks that changed are shown.

- **Rather than:** inventing a mid-session percentage; listing the whole
  unchanged ladder.
- **Gains:** rank reporting says only what the journal recorded.
- **Costs:** a session's percentage progress appears a session late.

## Honest figures

### A level is not an event

A level is a state the journal states outright: a balance, a rank
percentage, the current system. It carries forward from the last reading and
has an age as well as a value. An event belongs to its session alone. Every
level may be unread; the domain derives none of them.

- **Rather than:** folding everything from the session's moments.
- **Gains:** a session that read no balance no longer looks identical to one
  that earned nothing; a visited count is never zero, since a commander is
  always somewhere.
- **Costs:** every level has an unread case the report must word.

### An unread figure is left out unless its slot must be filled

Where a slot has to hold something, such as the balance on the credits card,
the report says there was no reading. Elsewhere an unmeasured figure is
omitted.

- **Rather than:** printing zero; announcing every quantity that went
  unmeasured, as the card's "Change unread" once did.
- **Gains:** no false zero; no page filling up with what was not measured.
- **Costs:** an absent figure is not always explained.

### The net credit change comes from the balances

The session's change is the difference between the first and last balance
the journal states. With fewer than two balances there is no change to
report.

- **Rather than:** totalling the credit deltas on moments, which price only
  income; a session that ended twenty million credits down reported a gain.
  Adding a spending rule per event would always be a game update behind.
- **Gains:** a rebuy, a refit or a hold of tritium counts against the player
  exactly as it did in the game.
- **Costs:** a session that states one balance has no change at all.

### The balance is dated, never derived

The journal states the balance only at login, so the report prints when the
reading was taken beneath it.

- **Rather than:** applying every priced event to the login balance. Measured
  against the next login's stated balance, that matched on two of fifty-four
  active sessions and was out by a median of about eight million credits;
  four sessions moved the balance with no priced event at all.
- **Gains:** no figure confidently wrong by millions.
- **Costs:** on a long session the headline is hours old; the report says so.

### What the priced events came to, in a card of its own

Beside the balance, a separate card totals every event the journal does
price, income less outgoings, with a note that it is not the balance change.

- **Rather than:** putting that total in the change slot; leaving the player
  with nothing when the change is unread.
- **Gains:** a session that sold eighty stored modules shows what they came
  to, even when the journal never restates the balance.
- **Costs:** two credit figures that routinely differ, which the labels have
  to keep apart.

### Spending has a channel of its own

A purchase cost is read from the field that states it (the total cost, the
buy price, the ship price, the transfer price) into a spend channel separate
from income and from distances.

- **Rather than:** the income channel, which counted spending as banked money
  and let a large purchase raise the major-payout milestone; borrowing the
  magnitude channel, which also carries jump distances in light years.
- **Gains:** spending can be totalled honestly; the priced total became
  possible. Giving a Vessel Hangar bay its price closed a 697,076 Cr gap on a
  real journal.
- **Costs:** a third channel through the taxonomy, the domain and the
  presenter.

### Merc Coins are a currency of their own

An Operation's Merc Coins ride their own channel and never join a credit
figure. The journal field they are read from is named in the taxonomy. A
missing field reads as zero in the domain and raises a notice in the report.

- **Rather than:** folding coins into credits; naming the field in code.
- **Gains:** a game-side rename is a one-line edit; a wrong field name is
  reported rather than hidden.
- **Costs:** the field name is an assumption no published source or local
  journal has yet confirmed.

### A rule that reads nothing says so

When a taxonomy rule names a currency or magnitude field the matching event
never carried (or carried in a form that could not be read), the report
shows a notice naming the event and the field.

- **Rather than:** quietly printing zero.
- **Gains:** a silent zero becomes visible the first time it happens. Watching
  magnitude too came from a jump-distance defect: the field was present and
  correctly named but went unread.
- **Costs:** a notices block a reader may see on an otherwise clean report.

### A carrier's distance is measured from positions

A carrier jump states where it arrived, not how far it came. The distance is
the gap between consecutive arrivals and the report says how many legs it
covers.

- **Rather than:** inventing an origin for the first jump; presenting a short
  total as the whole; leaving the distance out.
- **Gains:** a real distance with its gap stated.
- **Costs:** the first leg of a session is never measured.

### Material trades carry no credit figure

An exchange at a material trader is a trade moment, counted beside the market
figures in the Trade section. The journal states no price, so it joins
neither credit column.

- **Rather than:** pricing it with an invented figure; leaving it out, as
  happened while the event had no rule.
- **Gains:** a session that traded thirty-one times at the traders and bought
  nothing on a market reports both truthfully.
- **Costs:** none recorded.

### An experimental effect is told apart by a field's presence

Applying an experimental effect is reported by the journal as an engineering
roll. Only the applying event carries the field naming it as applied, so a
rule matches on that field being present.

- **Rather than:** matching on the effect's name, which every later roll on
  that module restates; one engineering count for both kinds of work.
- **Gains:** four effects and thirty rolls no longer read as thirty-four
  modifications.
- **Costs:** none recorded.

### Outfitting and the shipyard are counted per side

Modules and ships bought and sold each keep their own count and sum;
transfers have their own pair. The section states what the journal will not
let it count: a Vessel Hangar bay (counted under the vessel) and a ship taken
in part-exchange.

- **Rather than:** one net figure, which reports a big refit and a quiet
  session alike.
- **Gains:** a refit reads as what it was.
- **Costs:** more lines in the section.

### An event is filed by what the journal says it is

An approach to a settlement fires when the ship flies within range, so it
counts under Travel as a settlement approached, never under On Foot.

- **Rather than:** filing an event by what the player might have been doing.
- **Gains:** a card never reports a mode the commander never entered.
- **Costs:** wording that says only "Approached", even when the commander did
  land.

### The killer's ship is named from the scan before the kill

A death row names who destroyed the player, their ship, rank and squadron and
every attacker in a wing kill. The ship name comes from the targeting scan
that preceded the death. The row also names the vehicle actually lost and
the rebuy charged.

- **Rather than:** the raw model token the death event carries; naming the
  ship the session ended in.
- **Gains:** a death row stands alone months later.
- **Costs:** a death with no preceding scan has less to say.

## Words in the report

### The event taxonomy is data in TOML

The mapping from journal events to moments, the labels, icons, thresholds,
formats and history limits all live in one TOML file read with the standard
library. A test fails if a key a moment rule declares is never read.

- **Rather than:** event mappings and tuning values in code.
- **Gains:** a new journal event or a game-side rename is a config edit; the
  taxonomy can be reviewed on its own. The read-every-key test exists because
  the wording templates once parsed and were then ignored.
- **Costs:** a large configuration file that has to be kept in step with the
  rules that read it.

### Shared events are told apart in the taxonomy

Where one event covers several things, a rule names the field and the tokens
that pick it out; a rule may instead name a field whose presence does. The
first rule that matches wins, so the taxonomy's order sets precedence.

- **Rather than:** a branch per event name in the reducer; loadout or item
  names hardcoded in the domain.
- **Gains:** a new fighter variant is one line of configuration.
- **Costs:** rule order matters and has to be read with care.

### Row wording lives beside each rule and renders strictly

Each rule carries a template rendered against the raw journal entry. If the
entry lacks a name the template needs, the row falls back to its plain label.
The template engine sits in infrastructure behind a port.

- **Rather than:** wording hardcoded per event; a lenient render that prints
  a sentence with holes in it.
- **Gains:** an engineering roll names its blueprint, grade, module and
  engineer; a reader is never shown a gap they would take for a fact.
- **Costs:** a template mistake shows as a plain label rather than an error.

### Module names decoded from the token

The journal states no readable module name: across 182 fitted modules in a
real journal not one carried one. The English is decoded from the token's
parts, with the vocabulary in the taxonomy. A part with no entry is
title-cased and kept.

- **Rather than:** printing the token; a product dictionary in code; dropping
  parts the vocabulary does not know.
- **Gains:** a module reads as a 5D Sensors rather than a code; a vocabulary
  gap shows as an odd word rather than a missing one.
- **Costs:** one entry per part, so a part that means different things on
  different modules is left unmapped: "fast" reads as "Fast" on both.

### Journal time, labelled UTC, dated only when needed

Times are the journal's own UTC, shown unconverted and labelled so. A log
covering more than one day gets a heading per day, worked out separately for
each panel. The log runs newest first.

- **Rather than:** converting to local time; dating every row.
- **Gains:** a daylight-saving change cannot move a row to the wrong day; a
  single session keeps a narrow time column.
- **Costs:** the reader converts to local time in their head.

## The report and its files

### One self-contained HTML file, plus Markdown

A session report is one HTML file with its styles inlined and no JavaScript.
Markdown is the alternative for pasting into Discord or Reddit. HTML is the
default; the default can be changed and overridden per export.

- **Rather than:** a single format; a choice forced on every export.
- **Gains:** a report can be handed to somebody as one file; no script runs
  when it opens.
- **Costs:** none recorded.

### Reports land in Downloads and open in the browser

Reports are written to the player's Downloads folder (honouring a relocated
or renamed one) unless another folder is chosen, then opened in the default
browser.

- **Rather than:** a report viewer inside the program.
- **Gains:** no viewer to build; the report is a file the player already
  knows how to keep, open and share.
- **Costs:** the program cannot tell whether the report was read.

### The history report is a bundle of pages

The whole-history report is an index carrying the report and the newest
month, a page per calendar month and one shared stylesheet. A session report
stays one file.

- **Rather than:** one document that grows for ever and is rewritten whole
  on every quit.
- **Gains:** each page stays small; the bundle still opens from disk with no
  server and no script.
- **Costs:** the history report is a folder rather than a file.

### Pages keyed on the month they cover

A page is named for its calendar month and filled from the month's oldest
row. Rows per page are capped at a thousand and at a size budget of 512,000
bytes, whichever is stricter.

- **Rather than:** numbering pages by position, which renumbers every page
  when a new one is added.
- **Gains:** a finished month never changes, so its page is never rewritten.
- **Costs:** a very busy month can still fill a long page.

### Only what changed is written

The bundle writer compares the bytes it is about to write with what is on
disk and leaves an unchanged file alone. It removes pages the bundle no
longer holds, within its own pages folder only.

- **Rather than:** rewriting the whole bundle on every quit.
- **Gains:** a short session rewrites the index and the stylesheet and leaves
  every older page untouched, which a scale test checks.
- **Costs:** none recorded.

### The month list lives on the index alone

The index lists every month with its entry count. Each page links back to
that list by anchor and carries newer and older links.

- **Rather than:** the list on every page, which would rewrite every page each
  new month; stepping one page at a time.
- **Gains:** any month is two clicks from anywhere.
- **Costs:** reaching another month from a page goes through the index.

### Whole-history tab counts held in the stylesheet

A tab states its figure for the whole history. Those counts are generated
into the stylesheet, which is rewritten on every run anyway.

- **Rather than:** counts for the page alone, which mislead; counts in each
  page, which rewrite every page every session; a script to fill them in.
- **Gains:** honest counts without undoing the paging; still no JavaScript.
- **Costs:** figures carried in CSS, an unusual place for them.

### A rollup that bounds the report, offered but off

Rows older than ninety days can be folded into one row per day per category.
It is off by default because it discards detail. The age is measured back
from the newest row, never from the clock.

- **Rather than:** an unbounded report with no option; a rollup imposed on
  everyone; a threshold anchored to now.
- **Gains:** a player who wants a bounded report can have one; an unchanged
  journal renders the same way tomorrow.
- **Costs:** left off, the bundle gains a page a month for ever.

### One-document history, capped and saying so

A taxonomy setting writes the history as one document instead, keeping the
newest 2,000 entries; the footer states how many were left out. Markdown
history is capped the same way.

- **Rather than:** an uncapped single file.
- **Gains:** a single file can still be sent to somebody.
- **Costs:** older entries are not in it.

## The interface

### A tray program with a home window

There is no main window. A left click on the tray icon opens the home window,
holding the live status, both debrief actions and the reports made this run;
a right click opens the full menu.

- **Rather than:** a main window kept open beside the game.
- **Gains:** nothing on screen while the player flies.
- **Costs:** the program needs a tray (or the fallbacks below) to be reached.

### The desktop is asked whether it draws a tray

o7 Debrief asks Qt whether this desktop draws a tray, every half second for
up to fifteen seconds. With a tray the icon is shown; without one the home
window opens.

- **Rather than:** assuming a tray from the operating system; asking once.
  Started at sign-in the program is up before the panel that hosts the icon,
  so one early question reports no tray on a session about to have one.
- **Gains:** the program is never left running with nothing to click.
- **Costs:** a redundant window where a tray appears late; the answer is
  settled once and not tracked afterwards.

### One copy per user, held by the operating system

The single-instance guard is an exclusive operating-system lock on a file,
released when the process ends. Inside a Flatpak the lock and the summon
marker sit in the folder the sandbox shares between instances.

- **Rather than:** a lock file whose existence alone means "running".
- **Gains:** a crash or a reboot never leaves a stale lock.
- **Costs:** the shared Flatpak folder is written from the documented layout
  and not yet proven across two launches in the sandbox.

### Starting at sign-in is the player's choice

The setting writes a Run value on Windows and an XDG autostart entry on
Linux, through one shared shape. Under a Flatpak the entry is written to the
session's real autostart folder, ignoring the sandbox's redirected
configuration.

- **Rather than:** turning it on by default; honouring the sandbox's
  redirect, which wrote an entry nothing read and then read it back as on.
- **Gains:** the setting does what it says on both platforms.
- **Costs:** a Flatpak install cannot arrive with it on; it is one trip into
  Settings.

### No journal, said out loud

When no journal folder can be found, o7 Debrief writes the reason to stderr,
shows a dialog with the places it looked in the details and exits with code
one.

- **Rather than:** an uncaught error, which gave a traceback in a terminal
  and nothing at all from a launcher or the console-less Windows build.
- **Gains:** a machine without the game gets a sentence explaining why.
- **Costs:** none recorded.

## Building and installing

### Nuitka for Windows

The application is compiled with Nuitka into a standalone folder with the
console disabled.

- **Rather than:** asking players to install Python.
- **Gains:** a self-contained build.
- **Costs:** a C toolchain on the build machine; a slow first build.

### A Flatpak for Linux, with no standalone binary

Linux ships as a Flatpak built by a script that writes its own manifest,
desktop entry and metadata and fetches the wheels on the host so the
sandboxed build is offline. Running from source is the other supported way.

- **Rather than:** a Linux standalone binary, which the Nuitka build cannot
  produce because it carries Windows-only metadata.
- **Gains:** one artefact that runs on any distribution Flatpak serves.
- **Costs:** two packaging routes to maintain; two Flatpak assumptions remain
  untried (see TECH_DEBT.md item 2).

### A setup program of its own, per user

Install, upgrade, repair and removal are one bespoke program. It installs
under the user's own folders and registry, so it needs no administrator
rights. It imports nothing from the application. Its operations and state are
free of Qt; the Qt window drives them from a worker thread. Removing o7
Debrief deletes the user's settings only when asked.

- **Rather than:** a generic installer; the single module of over a thousand
  lines it once was.
- **Gains:** the privileged work sits inside the coverage gate; progress is
  real; a running copy can be closed for the player.
- **Costs:** the setup program is o7 Debrief's own to maintain; each account
  on a machine installs separately.

### The payload cannot write outside the install folder

Every archive entry is resolved against the install folder before extraction
and refused if it would land outside it.

- **Rather than:** trusting the bundle because the project built it.
- **Gains:** extraction running with the user's full rights cannot be steered
  elsewhere.
- **Costs:** none recorded.

### Close the running copy by name only

A running copy is ended with a forced terminate of the named program and
nothing else. A test pins the argument list.

- **Rather than:** a tree terminate, which twice took the setup program down
  with the application while the application closed perfectly.
- **Gains:** the setup program survives closing the application.
- **Costs:** none recorded; the application starts no child processes.

### The setup program writes down what it did

Each step is appended to a log in the temporary folder, with native crashes
and worker-thread failures captured there too. A launch after installing is
reported; the window stays open to say so when it fails.

- **Rather than:** a crash log alone; assuming the launch worked.
- **Gains:** the quiet failures (an install that reports success and starts
  nothing) leave evidence.
- **Costs:** a log file per run; logging is best effort and never fails an
  install.

### The build stamps the site and the example report

Both Windows build scripts stamp the website's version from the VERSION file
and regenerate the published example report, failing the build if either
fails.

- **Rather than:** steps somebody has to remember, which left the example
  report stating v0 for the life of the project.
- **Gains:** a release cannot ship a site that disagrees with the binary.
- **Costs:** a build touches files under the site folder.

### The running version is injected

The report footer states the version the composition root read from the
VERSION file. The presenter requires it as a keyword argument and a test
asserts the wiring.

- **Rather than:** a lookup with a default, which made every report ever
  written end with v0.
- **Gains:** no caller can produce a report without saying which version
  produced it.
- **Costs:** none recorded.

## Engineering

### Layers with one place where they meet

The code is split into domain, application, infrastructure and interface,
each depending only inward, with one composition root wiring them by
constructor. Structural tests hold the boundaries.

- **Rather than:** convention alone; a dependency injection framework.
- **Gains:** the rules about sessions and figures are tested with no disk,
  clock or screen.
- **Costs:** a port per outside concern and more explicit wiring.

### The domain never reads the clock

The domain works only in time taken from journal entries. A structural test
forbids I/O, logging and clock reads there. The one place that reads the
clock is an adapter behind a port.

- **Rather than:** reading the wall clock where convenient.
- **Gains:** the same journal always produces the same debrief.
- **Costs:** time has to be passed in wherever it is needed.

### Total coverage where it means something

Branch coverage must be total over the domain, the application layer, the
whole infrastructure layer and the setup program's operations and state.
Both Qt clients and the composition roots are tested but not held to a
figure.

- **Rather than:** one figure over everything, which would reward mocking the
  real world exactly where it must not be mocked; listing infrastructure's
  sub-packages one by one.
- **Gains:** a new adapter is gated the moment it is added; anything short of
  total in the gated code is a decision nobody made.
- **Costs:** a run can fail with every test passing, so the exit code has to
  be read.

### No magic numbers

A structural test forbids unexplained numeric literals in logic. Values come
from the taxonomy or from named constants.

- **Rather than:** literals written where they are used.
- **Gains:** a figure in a report about credits and ranks always says where
  it came from.
- **Costs:** small constants need names.

### Small modules

No module may exceed four hundred lines, across the package, the setup
program, the tests and the repository root. The composition root and three
delivery scripts are exempt by name, each with a reason; a test fails if an
exemption outlives its file.

- **Rather than:** letting files grow, as the setup program and the
  composition root once did unseen.
- **Gains:** modules split at real seams.
- **Costs:** many small files.

### Tests with real parts

No mocking library is used. Doubles are written by hand; Qt runs for real
under the offscreen platform; infrastructure is tested against sample
journals and real temporary folders.

- **Rather than:** mocks.
- **Gains:** a passing test means the real thing works.
- **Costs:** fakes are written and kept by hand.

### Worker results arrive on the interface thread

A result from a worker thread is delivered to a method of an object living on
the interface thread, so Qt queues it there. A test asserts the thread each
callback runs on.

- **Rather than:** connecting signals to bare functions, which Qt runs on the
  sending thread; the setup program once deadlocked waiting on the thread it
  was running in.
- **Gains:** no window is touched from the wrong thread.
- **Costs:** more ceremony around background work.

### Silent drift pinned by test

The Linux desktop identity, stated in the Flatpak script and in the names the
composition root gives Qt, is pinned by a test. So are the house prose rules
across every file that carries prose.

- **Rather than:** trusting two files to stay in step; a style rule held only
  by review.
- **Gains:** a one-character drift fails the suite rather than giving the
  home window a stray launcher icon.
- **Costs:** the prose test is the one file exempt from its own scan.

### flake8 is the linter of record; ruff is told to agree

black formats; flake8 is enforced. ruff is configured to enable the same
deferred-import rule, with four files told not to call their deliberate
markers unused.

- **Rather than:** ruff left unconfigured, whose autofix would have stripped
  those markers and broken the scripts they protect.
- **Gains:** a clean run of either linter means the same thing.
- **Costs:** four per-file exceptions to explain.
