"""Tests for HtmlBundleExporter: the files, the links and the shared sheet.

The bundle has to open from the filesystem with no server and no scripts, so
what is asserted here is that every page links a stylesheet that exists, every
navigation link points at a file the bundle contains, and no page carries a
figure that the next session would change.

British spelling is used in comments. No em dashes appear anywhere.
"""

from __future__ import annotations

import re

from o7debrief.application.services.history_paging import paginate
from o7debrief.domain.value_objects.enums import ActivityDomain, MomentKind
from o7debrief.infrastructure.render.html_bundle_exporter import (
    BUNDLE_DIRECTORY_NAME,
    HtmlBundleExporter,
)
from tests.application.history_builders import (
    history_options,
    moment_at,
    spread,
    view_of,
)

# A spacing that puts a few hundred rows across several months.
_MANY = 2000


def _bundle(moments, **overrides):
    """Render a bundle from these moments with any option overridden."""
    view = view_of(moments)
    options = history_options(**overrides)
    pages = paginate(view, options, dict(view.month_titles))
    return HtmlBundleExporter().render_bundle(view, pages), pages


def _by_path(bundle) -> dict[str, str]:
    """Return the bundle's files as decoded text, keyed by relative path."""
    return {item.relative_path: item.content.decode("utf-8") for item in bundle.files}


def test_the_bundle_names_a_stable_directory_and_an_openable_entry() -> None:
    """One directory rewritten in place, with an index a browser can open."""
    bundle, _pages = _bundle(spread(_MANY))

    assert bundle.directory_name == BUNDLE_DIRECTORY_NAME
    assert bundle.entry_point == "index.html"


def test_the_bundle_holds_one_stylesheet_an_index_and_a_page_each() -> None:
    """The newest page is the index; every older page is its own file."""
    bundle, pages = _bundle(spread(_MANY))
    files = _by_path(bundle)

    assert "style.css" in files
    assert "index.html" in files
    for page in pages[1:]:
        assert f"pages/{page.key}.html" in files
    assert len(files) == len(pages) + 1


def test_every_page_links_a_stylesheet_the_bundle_contains() -> None:
    """A link to a file that is not there is a page with no styling at all."""
    bundle, _pages = _bundle(spread(_MANY))
    files = _by_path(bundle)

    assert '<link rel="stylesheet" href="style.css">' in files["index.html"]
    for path, html in files.items():
        if path.startswith("pages/"):
            assert '<link rel="stylesheet" href="../style.css">' in html


def test_every_navigation_link_points_at_a_file_in_the_bundle() -> None:
    """Navigation reaches every page and never leaves the reader nowhere."""
    bundle, _pages = _bundle(spread(_MANY))
    files = _by_path(bundle)
    present = set(files)

    for path, html in files.items():
        if not path.endswith(".html"):
            continue
        here = path.rsplit("/", maxsplit=1)[0] if "/" in path else ""
        for href in re.findall(r'<a href="([^"]+)"', html):
            resolved = href
            if href.startswith("../"):
                resolved = href[len("../") :]
            elif here:
                resolved = f"{here}/{href}"
            assert resolved in present, f"{path} links missing {href}"


def test_the_index_has_no_newer_link_and_the_oldest_has_no_older_one() -> None:
    """The ends of the set say so rather than offering a dead link."""
    bundle, pages = _bundle(spread(_MANY))
    files = _by_path(bundle)

    assert '<span class="disabled">&larr; Newer</span>' in files["index.html"]
    oldest = files[f"pages/{pages[-1].key}.html"]
    assert '<span class="disabled">Older &rarr;</span>' in oldest
    assert '<a href="../index.html">Index</a>' in oldest


def test_a_single_page_history_needs_only_an_index() -> None:
    """One month of play is one file plus its sheet, not a bundle of one."""
    bundle, _pages = _bundle(spread(10, "2026-08-01T09:00:00Z"))
    files = _by_path(bundle)

    assert sorted(files) == ["index.html", "style.css"]
    assert '<span class="disabled">Older &rarr;</span>' in files["index.html"]


def test_an_empty_history_still_produces_a_readable_index() -> None:
    """A directory holding a stylesheet and nothing to open is not a report."""
    bundle, _pages = _bundle(())
    files = _by_path(bundle)

    assert sorted(files) == ["index.html", "style.css"]
    assert "No log entries" in files["index.html"]


def test_the_global_counts_live_in_the_stylesheet_not_in_the_pages() -> None:
    """The one arrangement that satisfies global tab counts and stable pages.

    A tab must state the whole history's figure, but that figure changes on
    every session. Held in each page's markup it would rewrite forty pages a
    quit; held in the one small sheet, the pages never move and the counts
    stay right.
    """
    bundle, pages = _bundle(spread(_MANY))
    files = _by_path(bundle)
    combat = next(tab for tab in pages[0].categories if tab.key == "combat")

    assert f'content: " of {combat.total_count}"' in files["style.css"]
    assert f'content: " of {pages[0].total_entries}"' in files["style.css"]
    for path, html in files.items():
        if path.endswith(".html"):
            assert f"of {combat.total_count}" not in html


def test_an_older_page_carries_nothing_the_next_session_would_change() -> None:
    """The journal span and the generation time belong on the index alone."""
    bundle, pages = _bundle(spread(_MANY))
    files = _by_path(bundle)
    older = files[f"pages/{pages[1].key}.html"]

    assert "Journal" not in older
    assert "Generated" not in older
    assert "All times shown in UTC" in older


def test_a_tab_with_nothing_on_this_page_says_so() -> None:
    """An empty panel is a dead end; a sentence is not."""
    bundle, _pages = _bundle(
        (
            moment_at("2026-07-10T09:00:00Z", ActivityDomain.TRAVEL),
            moment_at("2026-08-10T09:00:00Z", ActivityDomain.COMBAT, MomentKind.BOUNTY),
        )
    )
    files = _by_path(bundle)

    assert "No Combat entries on this page." in files["pages/2026-07.html"]
    assert "No Travel entries on this page." in files["index.html"]


def test_the_bundle_carries_no_script_of_any_kind() -> None:
    """Tabs and navigation are CSS and links, exactly as the one-file report."""
    bundle, _pages = _bundle(spread(_MANY))

    for item in bundle.files:
        assert b"<script" not in item.content
        assert b"javascript:" not in item.content
