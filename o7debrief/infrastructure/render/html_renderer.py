"""HtmlDebriefExporter: render a DebriefView as one self-contained HTML file.

This adapter implements the application ``DebriefExporter`` port for the
``html`` format. It produces a single dark "dossier" page in the Elite
Dangerous HUD palette, with every style inlined in one ``<style>`` block and no
JavaScript, so the file opens identically anywhere and can be shared as-is. It
consumes only the renderer contract returned by ``DebriefView.to_context()``;
every value it shows is already formatted; journal-derived text is HTML
escaped by the autoescaping template environment.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

from jinja2 import Environment

from o7debrief.application.dto.debrief_view import DebriefView
from o7debrief.infrastructure.render.html_styles import STYLESHEET
from o7debrief.infrastructure.render.icons import emoji_for

__all__ = ["HtmlDebriefExporter"]

# File-type suffix (no dot) this exporter produces; matched by the export
# service against the requested formats.
_EXTENSION = "html"
# Text encoding for the emitted bytes.
_ENCODING = "utf-8"
# Name under which the icon-to-emoji helper is exposed to the template.
_EMOJI_FILTER = "emoji"
# Context name under which the stylesheet receives the tab keys.
_TAB_KEYS = "tab_keys"

# The report as one self-contained template: the shared stylesheet inlined
# between the head and the body and no scripts anywhere.
_HEAD = """{% macro timeline_row(entry) -%}
{% if entry.day_separator %}      <li class="daysep">{{ entry.day_separator }}</li>
{% endif %}      <li>
        <span class="t">{{ entry.time_display }}</span>
        <span class="ico">{{ entry.icon | emoji }}</span>
        <span>
          <span class="mode" title="{{ entry.mode_label }}">{{ entry.mode_tag }}</span>
          {{ entry.text }}{% if entry.system %}
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
"""

_BODY = """</style>
</head>
<body>
<div class="wrap">
  <h1>Commander Mission Debrief</h1>
  <p class="sub">CMDR {{ header.commander }} &middot; {{ header.ship }}
  {%- if header.ship_name %} &middot; &ldquo;{{ header.ship_name }}&rdquo;{% endif -%}
  </p>

  <div class="panel meta">
    <div><span>Session start</span>{{ header.session_start }}</div>
    <div><span>Session end</span>{{ header.session_end }}</div>
    <div><span>Duration</span>{{ header.duration }}</div>
    <div class="route"><span>Route</span>{{ header.start_system
      }}<span class="arrow">&rarr;</span>{{ header.end_system }}</div>
    <div><span>Systems visited</span>{{ header.systems_visited }}</div>
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
        {% if rank.progress_pct is none %}
        <span class="neutral">{{ rank.progress_display }}</span>
        {% else %}
        <span class="rank-bar" title="{{ rank.progress_display }}">
        <span class="rank-fill" style="width: {{ rank.progress_pct }}%"></span></span>
        {% endif %}
      </li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}

  {% if notices %}
  <h2>Notices</h2>
  <div class="panel">
    <ul class="milestones">
      {% for notice in notices %}
      <li>{{ notice }}</li>
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
    {%- if footer.timezone %}<br>
    All times shown in {{ footer.timezone }}, as the journal records them.
    {%- endif %}
    {%- if footer.truncation_notice %}<br>
    <span class="trunc">{{ footer.truncation_notice }}</span>
    {%- endif %}
  </footer>
</div>
</body>
</html>
"""

# One template: the head, the shared sheet, then the body.
_TEMPLATE = _HEAD + STYLESHEET + _BODY


class HtmlDebriefExporter:
    """Renders a DebriefView into self-contained HTML (port: DebriefExporter)."""

    extension = _EXTENSION

    def __init__(self) -> None:
        environment = Environment(autoescape=True)
        environment.filters[_EMOJI_FILTER] = emoji_for
        self._template = environment.from_string(_TEMPLATE)

    def render(self, view: DebriefView) -> bytes:
        """Render the view's context into self-contained HTML bytes."""
        context = view.to_context()
        # The stylesheet needs the category keys alone, not the categories, so
        # the same sheet serves the bundle's pages without knowing their shape.
        context[_TAB_KEYS] = [
            category["key"] for category in context["timeline_categories"]
        ]
        return self._template.render(**context).encode(_ENCODING)
