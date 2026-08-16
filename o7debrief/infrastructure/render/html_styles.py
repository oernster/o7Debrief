"""The report stylesheet, shared by the single-file report and the bundle.

One sheet serves both, so the palette, the typography and the log layout
cannot drift apart between a session report and a history report. The
single-file report inlines it inside its one document; the bundle writes it
once as ``style.css`` and every page links to it, rather than repeating the
whole ``:root`` block on each of forty pages.

It is Jinja source rather than plain CSS because the tab rules depend on which
categories the report holds: a checked radio shows its own panel, so there is
one rule per category. ``tab_keys`` carries those category keys and is the
only thing the sheet needs to know about the report.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

__all__ = ["STYLESHEET"]

STYLESHEET = """:root {
  --bg: #0d0d10; --panel: #16161d; --edge: #2a2a33;
  --accent: #f07b05; --accent-soft: #f8a24a;
  --text: #d7d7da; --muted: #8a8a93;
  --pos: #5fd07a; --neg: #e06f6f; --neutral: #8a8a93;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2rem 1rem; background: var(--bg); color: var(--text);
  font-family: "Consolas", "DejaVu Sans Mono", monospace; line-height: 1.5;
}
.wrap { max-width: 60rem; margin: 0 auto; }
h1 { color: var(--accent); font-size: 1.6rem; margin: 0 0 0.25rem;
  letter-spacing: 0.04em; }
h2 { color: var(--accent-soft); font-size: 1.05rem; text-transform: uppercase;
  letter-spacing: 0.04em; border-bottom: 1px solid var(--edge);
  padding-bottom: 0.3rem; margin: 2rem 0 1rem; }
.sub { color: var(--muted); margin: 0 0 1.5rem; }
.panel { background: var(--panel); border: 1px solid var(--edge);
  border-radius: 6px; padding: 1rem 1.2rem; }
.meta { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 0.6rem 1.5rem; }
.meta span { color: var(--muted); font-size: 0.78rem; text-transform: uppercase;
  display: block; }
/* The route is one cell, not a From cell and a To cell. As two they wrapped
   apart, leaving the origin at the end of one row and the destination at the
   start of the next, which read as two unrelated facts. */
.meta .route .arrow { display: inline; color: var(--muted); padding: 0 0.4rem;
  font-size: 1rem; text-transform: none; }
.grid { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 1rem; }
.metric { background: var(--panel); border: 1px solid var(--edge);
  border-radius: 6px; padding: 0.9rem 1rem; }
.metric .label { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; }
.metric .value { font-size: 1.5rem; color: var(--accent); margin-top: 0.2rem; }
.metric .delta { font-size: 0.85rem; margin-top: 0.2rem; }
/* States how the value above should be read: for the balance, when it was
   taken. The journal names a balance only at a login, so a figure hours old
   would otherwise be read as the balance now. */
.metric .hint { color: var(--muted); font-size: 0.78rem; margin-top: 0.2rem; }
.positive { color: var(--pos); } .negative { color: var(--neg); }
.neutral { color: var(--neutral); }
.card .title { color: var(--accent-soft); font-size: 1rem; margin-bottom: 0.5rem; }
.stats { list-style: none; margin: 0; padding: 0; }
/* A stat row is a label and a figure on one line. The gap stops them touching
   when the label is long ("Modifications261"); the figure never wraps, because a
   value broken across two lines ("766.5" then "ly") stops reading as one
   quantity and no longer lines up with the figures above and below it. The
   label may wrap instead, since prose survives wrapping and a number does not. */
.stats li { display: flex; flex-wrap: wrap; justify-content: space-between;
  align-items: baseline; gap: 0.9rem; border-bottom: 1px dotted var(--edge);
  padding: 0.25rem 0; }
/* The label never shrinks below the widest word it holds. It carried
   min-width: 0, which lets a flex item collapse past its own content: with a
   long figure beside it the box went to zero width while the text carried on
   painting, so "Earned from modules" ran straight under "1,966,278,800 Cr".
   Keeping its intrinsic minimum means the row wraps instead, which is what
   flex-wrap above is for: the figure takes a line of its own rather than
   sharing one it does not fit on. */
.stats li span:first-child { color: var(--muted); }
/* margin-left: auto right-aligns the figure whether it shares the label's line
   or has wrapped onto its own, where space-between alone would leave it left. */
.stats li span:last-child { white-space: nowrap; text-align: right;
  flex: 0 1 auto; margin-left: auto; font-variant-numeric: tabular-nums; }
/* A qualification of the figure above it ("over 0 of 1 jumps"), on its own
   line. It is prose, so it wraps where the figure may not; carried inside the
   figure's own string it made the whole cell unbreakable and a long one ran
   out of the card and over the panel beside it. */
.stats .qual { display: block; white-space: normal; color: var(--muted);
  font-size: 0.85rem; }
.note { color: var(--muted); font-style: italic; margin-top: 0.5rem; }
.timeline { list-style: none; margin: 0; padding: 0; }
.timeline li { display: grid; grid-template-columns: 5.5rem 2rem 1fr; gap: 0.5rem;
  padding: 0.3rem 0; border-bottom: 1px solid var(--edge); }
/* A day heading in a log that spans several days. It is a block, not a grid
   row, because each log row is its own grid rather than the list being one, so
   there are no shared columns for it to span. */
.timeline li.daysep { display: block; color: var(--accent-soft);
  font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em;
  padding: 0.7rem 0 0.25rem; }
.timeline .t { color: var(--muted); }
.timeline .mode { color: var(--muted); font-size: 0.78rem; }
.timeline .sys { color: var(--accent-soft); }
.logtabs-radio { position: absolute; left: -9999px; opacity: 0; }
.logtabs { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0 0 0.8rem; }
.logtabs label { cursor: pointer; padding: 0.3rem 0.7rem;
  border: 1px solid var(--edge); border-radius: 4px; color: var(--muted);
  font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; }
.logtabs label:hover { color: var(--text); border-color: var(--accent-soft); }
.logpanel { display: none; }
{% if tab_keys %}
#logtab-all:checked ~ #panel-all { display: block; }
#logtab-all:checked ~ .logtabs label[for="logtab-all"] {
  background: var(--accent); color: var(--bg); border-color: var(--accent); }
{% for key in tab_keys %}
#logtab-{{ key }}:checked ~ #panel-{{ key }} { display: block; }
#logtab-{{ key }}:checked ~ .logtabs label[for="logtab-{{ key }}"] {
  background: var(--accent); color: var(--bg); border-color: var(--accent); }
{% endfor %}
{% endif %}
.ranks, .milestones { list-style: none; margin: 0; padding: 0; }
.ranks li, .milestones li { padding: 0.35rem 0; border-bottom: 1px solid var(--edge); }
.ranks li { display: flex; align-items: center; justify-content: space-between;
  gap: 1rem; }
.rank-bar { flex: 0 0 8rem; height: 0.55rem; background: var(--edge);
  border-radius: 3px; overflow: hidden; }
.rank-fill { display: block; height: 100%; background: var(--accent); }
.promoted { color: var(--accent); }
footer { color: var(--muted); font-size: 0.8rem; margin-top: 2.5rem;
  border-top: 1px solid var(--edge); padding-top: 1rem; }
/* Paged history only: the page heading, its navigation and the notes a page
   shows when a tab or the whole report is not the complete picture. */
.pagenav { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: baseline;
  margin: 1rem 0; }
.pagenav a { color: var(--accent-soft); text-decoration: none;
  border: 1px solid var(--edge); border-radius: 4px; padding: 0.3rem 0.7rem;
  font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; }
.pagenav a:hover { color: var(--text); border-color: var(--accent-soft); }
/* An unavailable direction keeps its place rather than letting the row
   reflow, so Older sits in the same spot on every page of the set. */
.pagenav .disabled { color: var(--muted); border: 1px solid transparent;
  padding: 0.3rem 0.7rem; font-size: 0.8rem; text-transform: uppercase;
  letter-spacing: 0.03em; }
.pagenav .where { color: var(--muted); font-size: 0.8rem; margin-left: auto; }
.pagetitle { color: var(--accent-soft); font-size: 0.9rem;
  text-transform: uppercase; letter-spacing: 0.04em; margin: 0 0 0.5rem; }
.emptytab { color: var(--muted); font-style: italic; margin: 0; }
/* Every month in the history, on the index. It reads as a row of small chips
   like the tab row above it, so the two scan as one navigation block. */
.monthlist { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: baseline;
  margin: 0 0 0.8rem; }
.monthlist .monthlabel { color: var(--muted); font-size: 0.78rem;
  text-transform: uppercase; letter-spacing: 0.04em; margin-right: 0.2rem; }
.monthlist a, .monthlist .current { padding: 0.25rem 0.6rem;
  border: 1px solid var(--edge); border-radius: 4px; font-size: 0.78rem;
  text-decoration: none; letter-spacing: 0.03em; }
.monthlist a { color: var(--muted); }
.monthlist a:hover { color: var(--text); border-color: var(--accent-soft); }
.monthlist a .n, .monthlist .current .n { color: var(--muted);
  padding-left: 0.35rem; }
.monthlist .current { background: var(--accent); color: var(--bg);
  border-color: var(--accent); }
.monthlist .current .n { color: var(--bg); }
/* The whole history's counts live here rather than in each page's markup.
   A tab must state the global figure (two here out of thirteen altogether)
   but a figure that grows every session would change the text of all forty
   pages on every quit and defeat the incremental write. The sheet is one
   small file rewritten each run, so putting the totals in it keeps both: the
   pages state only what is on them and never move and the totals stay right.
   No JavaScript is involved; these are ordinary generated-content rules. */
{% for tab in tab_totals %}
.logtabs label[for="logtab-{{ tab.key }}"] .n::after {
  content: " of {{ tab.total }}"; }
{% endfor %}
{% if tab_totals %}
.logtabs label[for="logtab-all"] .n::after { content: " of {{ all_total }}"; }
.pagenav .where::after { content: " of {{ page_total }}"; }
{% endif %}
.trunc { color: var(--neg); margin-top: 0.5rem; }
"""
