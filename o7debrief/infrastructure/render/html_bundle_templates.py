"""Jinja sources for the paged history bundle: its index and its pages.

The index is the whole report, ending with the newest page of the log. A page
file is the log alone, under the same heading and the same navigation. Both
link one shared ``style.css`` rather than repeating the stylesheet, which is
the point of the bundle: forty pages cost one copy of the palette, not forty.

The log section and the navigation are one source each, used by both, so the
two can never drift apart. Navigation is plain links and the tabs are still
the radio-and-sibling-selector arrangement the single-file report uses, so a
bundle needs no more JavaScript than the one-file report does, which is none.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

__all__ = ["INDEX_TEMPLATE", "PAGE_TEMPLATE"]

# One log row, plus the day heading above it when this page starts a new day.
_ROW_MACRO = """{% macro timeline_row(entry) -%}
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
"""

# Prev, next and index links. A direction with nowhere to go keeps its slot as
# plain text, so Older sits in the same place on every page of the set.
_NAV = """  <div class="pagenav">
    {% if nav.newer %}<a href="{{ nav.newer }}">&larr; Newer</a>
    {% else %}<span class="disabled">&larr; Newer</span>{% endif %}
    {% if nav.older %}<a href="{{ nav.older }}">Older &rarr;</a>
    {% else %}<span class="disabled">Older &rarr;</span>{% endif %}
    {% if nav.index %}<a href="{{ nav.index }}">Index</a>{% endif %}
    <span class="where">Page {{ nav.position }}</span>
  </div>
"""

# The tabbed log for one page. Every tab states the whole history's count and
# how many of those are here, so a reader is never left wondering whether a
# figure describes this page or the lot.
_LOG = """  <h2>Session log</h2>
  <p class="pagetitle">{{ page.title }}</p>
"""
_LOG += _NAV
_LOG += """  <input type="radio" name="logtab" id="logtab-all"
    class="logtabs-radio" checked>
  {% for cat in page.categories %}
  <input type="radio" name="logtab" id="logtab-{{ cat.key }}" class="logtabs-radio">
  {% endfor %}
  <div class="logtabs">
    <label for="logtab-all">All <span class="n">{{ page.entries | length
      }}</span></label>
    {% for cat in page.categories %}
    <label for="logtab-{{ cat.key }}">
      {{ cat.icon | emoji }} {{ cat.label }}
      <span class="n">{{ cat.page_count }}</span></label>
    {% endfor %}
  </div>
  <div class="panel logpanel" id="panel-all">
    <ul class="timeline">
      {% for entry in page.entries %}{{ timeline_row(entry) }}{% endfor %}
    </ul>
  </div>
  {% for cat in page.categories %}
  <div class="panel logpanel" id="panel-{{ cat.key }}">
    {% if cat.entries %}
    <ul class="timeline">
      {% for entry in cat.entries %}{{ timeline_row(entry) }}{% endfor %}
    </ul>
    {% else %}
    <p class="emptytab">No {{ cat.label }} entries on this page.</p>
    {% endif %}
  </div>
  {% endfor %}
"""

_PAGE_FOOTER = """  <footer>
    {{ footer.app_name }} v{{ footer.app_version }} &middot; {{ footer.license }}
    {%- if footer.timezone %}<br>
    All times shown in {{ footer.timezone }}, as the journal records them.
    {%- endif %}
  </footer>
</div>
</body>
</html>
"""

_FOOTER = """  <footer>
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


def _document(title: str, stylesheet_href: str, body: str, footer: str) -> str:
    """Return a full page: head, linked stylesheet, wrapped body, footer."""
    return (
        _ROW_MACRO
        + '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        + '<meta charset="utf-8">\n'
        + '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + f"<title>{title}</title>\n"
        + f'<link rel="stylesheet" href="{stylesheet_href}">\n'
        + '</head>\n<body>\n<div class="wrap">\n'
        + body
        + footer
    )


_INDEX_BODY = """  <h1>Commander Mission Debrief</h1>
  <p class="sub">CMDR {{ header.commander }} &middot; {{ header.ship }}
  {%- if header.ship_name %} &middot; &ldquo;{{ header.ship_name }}&rdquo;{% endif -%}
  </p>

  <div class="panel meta">
    <div><span>History start</span>{{ header.session_start }}</div>
    <div><span>History end</span>{{ header.session_end }}</div>
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

"""

_PAGE_BODY = """  <h1>Commander Mission Debrief</h1>
  <p class="sub">CMDR {{ header.commander }} &middot; history log</p>

"""

INDEX_TEMPLATE = _document(
    "{{ footer.app_name }} - Commander {{ header.commander }}",
    "style.css",
    _INDEX_BODY + _LOG,
    _FOOTER,
)

PAGE_TEMPLATE = _document(
    "{{ footer.app_name }} - {{ page.title }}",
    "../style.css",
    _PAGE_BODY + _LOG,
    _PAGE_FOOTER,
)
