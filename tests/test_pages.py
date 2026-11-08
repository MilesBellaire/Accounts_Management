"""Smoke tests: every page runs top to bottom without raising.

These hit the real database read-only (no page writes anything until a button is pressed),
so they check wiring rather than figures.
"""

import pytest
from streamlit.testing.v1 import AppTest

from conftest import SRC_ROOT

WEB_ROOT = SRC_ROOT.parent / 'web'

PAGES = [
	WEB_ROOT / 'app.py',
	*sorted(WEB_ROOT.glob('pages/*.py')),
]


@pytest.mark.parametrize('page', PAGES, ids=lambda p: p.stem)
def test_page_runs_without_exception(page):
	app = AppTest.from_file(str(page), default_timeout=90).run()

	assert not app.exception, [e.message for e in app.exception]


@pytest.mark.parametrize('page', PAGES, ids=lambda p: p.stem)
def test_page_reports_no_errors(page):
	"""st.error is how a page surfaces a problem to the user; none should fire on load."""
	app = AppTest.from_file(str(page), default_timeout=90).run()

	assert not app.error, [e.value for e in app.error]
