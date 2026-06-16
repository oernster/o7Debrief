"""HtmlDebriefExporter: render a DebriefView as one self-contained HTML file.

This adapter implements the application ``DebriefExporter`` port for the
``html`` format. It produces a single dark "dossier" page in the Elite
Dangerous HUD palette, with every style inlined in one ``<style>`` block and no
JavaScript, so the file opens identically anywhere and can be shared as-is. It
consumes only the renderer contract returned by ``DebriefView.to_context()``;
every value it shows is already formatted, and journal-derived text is HTML
escaped by the autoescaping template environment.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from jinja2 import Environment

from o7debrief.application.dto.debrief_view import DebriefView
from o7debrief.infrastructure.render.icons import emoji_for

__all__ = ["HtmlDebriefExporter"]

# File-type suffix (no dot) this exporter produces; matched by the export
# service against the requested formats.
_EXTENSION = "html"
# Text encoding for the emitted bytes.
_ENCODING = "utf-8"
# Name under which the icon-to-emoji helper is exposed to the template.
_EMOJI_FILTER = "emoji"

# The whole report as one self-contained template: all CSS inlined, no scripts.
_TEMPLATE = """{% macro timeline_row(entry) -%}
      <li>
        <span class="t">{{ entry.time_display }}</span>
        <span title="{{ entry.mode_label }}">{{ entry.mode_icon | emoji }}</span>
        <span>{{ entry.text }}{% if entry.system %}
          <span class="sys">{{ entry.system }}</span>{% endif %}</span>
      </li>
{%- endmacro -%}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ footer.app_name }} - Commander {{ header.commander }}</title>
<style>
:root {
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
.meta span { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; }
.grid { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: 1rem; }
.metric { background: var(--panel); border: 1px solid var(--edge);
  border-radius: 6px; padding: 0.9rem 1rem; }
.metric .label { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; }
.metric .value { font-size: 1.5rem; color: var(--accent); margin-top: 0.2rem; }
.metric .delta { font-size: 0.85rem; margin-top: 0.2rem; }
.positive { color: var(--pos); } .negative { color: var(--neg); }
.neutral { color: var(--neutral); }
.card .title { color: var(--accent-soft); font-size: 1rem; margin-bottom: 0.5rem; }
.stats { list-style: none; margin: 0; padding: 0; }
.stats li { display: flex; justify-content: space-between;
  border-bottom: 1px dotted var(--edge); padding: 0.2rem 0; }
.stats li span:first-child { color: var(--muted); }
.note { color: var(--muted); font-style: italic; margin-top: 0.5rem; }
.timeline { list-style: none; margin: 0; padding: 0; }
.timeline li { display: grid; grid-template-columns: 5.5rem 2rem 1fr; gap: 0.5rem;
  padding: 0.3rem 0; border-bottom: 1px solid var(--edge); }
.timeline .t { color: var(--muted); }
.timeline .sys { color: var(--accent-soft); }
.logtabs-radio { position: absolute; left: -9999px; opacity: 0; }
.logtabs { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0 0 0.8rem; }
.logtabs label { cursor: pointer; padding: 0.3rem 0.7rem;
  border: 1px solid var(--edge); border-radius: 4px; color: var(--muted);
  font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; }
.logtabs label:hover { color: var(--text); border-color: var(--accent-soft); }
.logpanel { display: none; }
{% if timeline %}
#logtab-all:checked ~ #panel-all { display: block; }
#logtab-all:checked ~ .logtabs label[for="logtab-all"] {
  background: var(--accent); color: var(--bg); border-color: var(--accent); }
{% for cat in timeline_categories %}
#logtab-{{ cat.key }}:checked ~ #panel-{{ cat.key }} { display: block; }
#logtab-{{ cat.key }}:checked ~ .logtabs label[for="logtab-{{ cat.key }}"] {
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
</style>
</head>
<body>
<div class="wrap">
  <h1>Commander Mission Debrief</h1>
  <p class="sub">CMDR {{ header.commander }} &middot; {{ header.ship }}</p>

  <div class="panel meta">
    <div><span>Session start</span><br>{{ header.session_start }}</div>
    <div><span>Session end</span><br>{{ header.session_end }}</div>
    <div><span>Duration</span><br>{{ header.duration }}</div>
    <div><span>From</span><br>{{ header.start_system }}</div>
    <div><span>To</span><br>{{ header.end_system }}</div>
    <div><span>Systems visited</span><br>{{ header.systems_visited }}</div>
  </div>

  <h2>Headline</h2>
  <div class="grid">
    {% for item in headline %}
    <div class="metric">
      <div class="label">{{ item.label }}</div>
      <div class="value">{{ item.value_display }}</div>
      {% if item.delta_display %}
      <div class="delta {{ item.delta_class }}">{{ item.delta_display }}</div>
      {% endif %}
    </div>
    {% endfor %}
  </div>

  {% if domains %}
  <h2>Activity</h2>
  <div class="grid">
    {% for domain in domains %}
    <div class="panel card">
      <div class="title">{{ domain.icon | emoji }} {{ domain.title }}</div>
      <ul class="stats">
        {% for stat in domain.stats %}
        <li><span>{{ stat.label }}</span><span>{{ stat.value_display }}</span></li>
        {% endfor %}
      </ul>
      {% if domain.note %}<div class="note">{{ domain.note }}</div>{% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}

  {% if ranks %}
  <h2>Rank progress</h2>
  <div class="panel">
    <ul class="ranks">
      {% for rank in ranks %}
      <li>
        <span class="rank-text">
        <strong{% if rank.promoted %} class="promoted"{% endif %}>
          {{ rank.ladder_title }}</strong>:
        {% if rank.promoted %}{{ rank.from_tier_name }} &rarr; {{ rank.to_tier_name }}
        {% else %}{{ rank.to_tier_name }}
        <span class="neutral">{{ rank.note }}</span>{% endif %}</span>
        <span class="rank-bar" title="{{ rank.progress_pct }}%">
        <span class="rank-fill" style="width: {{ rank.progress_pct }}%"></span></span>
      </li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}

  {% if milestones %}
  <h2>Milestones</h2>
  <div class="panel">
    <ul class="milestones">
      {% for milestone in milestones %}
      <li>{{ milestone.icon | emoji }} {{ milestone.text }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}

  {% if timeline %}
  <h2>Session log</h2>
  <input type="radio" name="logtab" id="logtab-all" class="logtabs-radio" checked>
  {% for cat in timeline_categories %}
  <input type="radio" name="logtab" id="logtab-{{ cat.key }}" class="logtabs-radio">
  {% endfor %}
  <div class="logtabs">
    <label for="logtab-all">All ({{ timeline | length }})</label>
    {% for cat in timeline_categories %}
    <label for="logtab-{{ cat.key }}">
      {{ cat.icon | emoji }} {{ cat.label }} ({{ cat.count }})</label>
    {% endfor %}
  </div>
  <div class="panel logpanel" id="panel-all">
    <ul class="timeline">
      {% for entry in timeline %}{{ timeline_row(entry) }}{% endfor %}
    </ul>
  </div>
  {% for cat in timeline_categories %}
  <div class="panel logpanel" id="panel-{{ cat.key }}">
    <ul class="timeline">
      {% for entry in cat.entries %}{{ timeline_row(entry) }}{% endfor %}
    </ul>
  </div>
  {% endfor %}
  {% endif %}

  <footer>
    {{ footer.app_name }} v{{ footer.app_version }} &middot; {{ footer.license }}<br>
    {% if footer.generated %}Generated {{ footer.generated }} &middot; {% endif %}
    Journal {{ footer.journal_first }} to {{ footer.journal_last }}
  </footer>
</div>
</body>
</html>
"""


class HtmlDebriefExporter:
    """Renders a DebriefView into self-contained HTML (port: DebriefExporter)."""

    extension = _EXTENSION

    def __init__(self) -> None:
        environment = Environment(autoescape=True)
        environment.filters[_EMOJI_FILTER] = emoji_for
        self._template = environment.from_string(_TEMPLATE)

    def render(self, view: DebriefView) -> bytes:
        """Render the view's context into self-contained HTML bytes."""
        html = self._template.render(**view.to_context())
        return html.encode(_ENCODING)
