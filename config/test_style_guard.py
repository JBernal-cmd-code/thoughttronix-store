"""Style guard: every page template follows the frontend conventions.

See ``docs/FRONTEND.md``. Pages extend a base template and style themselves
with Tailwind + DaisyUI classes only — no inline CSS, no extra stylesheets.
"""

import re

import pytest
from django.conf import settings

TEMPLATES_DIR = settings.BASE_DIR / "templates"
CSS_DIR = settings.BASE_DIR / "assets" / "css"

BASES = {"base.html", "backoffice/base.html"}

# Tailwind input and its compiled output. Anything else in assets/css is a
# stylesheet that bypasses the theme.
ALLOWED_CSS = {"source.css", "tailwind.css"}
# Known stragglers, pending removal. Delete the entry when the file goes.
LEGACY_CSS = {"marketing.css"}

EXTENDS = re.compile(r"""\{%\s*extends\s+["']([^"']+)["']\s*%\}""")
# An inline style is allowed only when its value is computed in the template
# (e.g. a chart bar's width) — something a static class can't express.
STATIC_INLINE_STYLE = re.compile(r'style="(?![^"]*(\{\{|\{%))[^"]*"')


def page_templates():
    """Every template that renders a full page: not a partial, not a base."""
    pages = []
    for path in sorted(TEMPLATES_DIR.rglob("*.html")):
        name = path.relative_to(TEMPLATES_DIR).as_posix()
        if "partials/" in name or name in BASES:
            continue
        pages.append(pytest.param(path, id=name))
    return pages


@pytest.mark.parametrize("path", page_templates())
def test_page_extends_a_base_template(path):
    match = EXTENDS.search(path.read_text(encoding="utf-8"))

    assert match, "page must {% extends %} base.html or backoffice/base.html"
    assert match.group(1) in BASES


@pytest.mark.parametrize("path", page_templates())
def test_page_has_no_custom_css(path):
    source = path.read_text(encoding="utf-8")

    assert "<style" not in source
    assert 'rel="stylesheet"' not in source
    assert not STATIC_INLINE_STYLE.search(source), "use Tailwind classes"


def test_no_stray_stylesheets():
    stylesheets = {path.name for path in CSS_DIR.glob("*.css")}

    assert stylesheets - ALLOWED_CSS - LEGACY_CSS == set()
