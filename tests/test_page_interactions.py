"""Exercise the page branches a default load does not reach.

A plain AppTest run only takes each widget's default, so the alternative periods, the
take-home toggle and the transaction filters would otherwise go unchecked.
"""

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from conftest import WEB_ROOT


def run(page, timeout=90):
	return AppTest.from_file(str(page), default_timeout=timeout).run()


def assert_clean(app):
	assert not app.exception, [e.message for e in app.exception]
	assert not app.error, [e.value for e in app.error]


@pytest.mark.parametrize('period', ['All time', 'This month', 'Month', 'Custom range'])
def test_dashboard_periods(period):
	app = run(WEB_ROOT / 'app.py')
	app.radio[0].set_value(period).run()

	assert_clean(app)


@pytest.mark.parametrize('takehome', [False, True])
def test_plan_takehome_toggle(takehome):
	app = run(WEB_ROOT / 'pages' / '6_Plan.py')
	app.toggle[0].set_value(takehome).run()

	assert_clean(app)
	assert len(app.dataframe) >= 1


@pytest.mark.parametrize('transfers', ['Include', 'Exclude', 'Only transfers'])
def test_transaction_transfer_filter(transfers):
	app = run(WEB_ROOT / 'pages' / '1_Transactions.py')
	app.selectbox(key='filter_transfers').set_value(transfers).run()

	assert_clean(app)


def test_transaction_search_filter():
	app = run(WEB_ROOT / 'pages' / '1_Transactions.py')
	app.text_input(key='filter_search').set_value('zzz-no-such-description').run()

	assert_clean(app)
	# An empty result set should be an info message, not a crash.
	assert any('No transactions match' in i.value for i in app.info)


def test_transaction_search_quote_is_not_sql():
	"""A quote in the search box must be bound as a parameter, not spliced into SQL."""
	app = run(WEB_ROOT / 'pages' / '1_Transactions.py')
	app.text_input(key='filter_search').set_value("'; drop table transact; --").run()

	assert_clean(app)


@pytest.mark.parametrize('tab_page', ['3_Budgets.py', '4_Incomes.py'])
def test_crud_pages_reject_bad_names(tab_page):
	"""The add form should refuse a name with a space rather than write it."""
	app = run(WEB_ROOT / 'pages' / tab_page)
	app.text_input(key='add_name').set_value('has a space').run()

	assert_clean(app)
	assert any('cannot contain spaces' in w.value for w in app.warning)


@pytest.mark.parametrize('tab_page', ['3_Budgets.py', '4_Incomes.py'])
def test_crud_pages_reject_duplicate_names(tab_page):
	app = run(WEB_ROOT / 'pages' / tab_page)
	existing = app.selectbox(key='edit_choice').value
	app.text_input(key='add_name').set_value(existing).run()

	assert_clean(app)
	assert any('already exists' in w.value for w in app.warning)


@pytest.mark.parametrize(
	'page, table',
	[('3_Budgets.py', 'budget'), ('4_Incomes.py', 'income')],
)
def test_edit_form_follows_the_selection(page, table):
	"""Switching the record must reload its values, not keep the previous record's.

	Streamlit ignores value=/index= once a widget key holds state, so the edit widgets are
	keyed per record id; this checks that actually happens.
	"""
	from database.io.dbio import sql

	names = getattr(sql, table).get()['name'].tolist()
	if table == 'income':
		names = [n for n in names if n != 'other']
	if len(names) < 2:
		pytest.skip('need at least two records to switch between')

	first, second = names[0], names[1]
	app = run(WEB_ROOT / 'pages' / page)

	app.selectbox(key='edit_choice').set_value(first).run()
	assert_clean(app)
	shown_first = [t.value for t in app.text_input if t.label == 'Name']

	app.selectbox(key='edit_choice').set_value(second).run()
	assert_clean(app)
	shown_second = [t.value for t in app.text_input if t.label == 'Name']

	assert first in shown_first, f'expected {first}, got {shown_first}'
	assert second in shown_second, f'switching to {second} still shows {shown_second}'


@pytest.mark.parametrize(
	'period',
	['This month', 'Previous month', 'Month', 'Last 3 months', 'Last 12 months', 'Custom range'],
)
def test_plan_vs_actual_periods(period):
	app = run(WEB_ROOT / 'pages' / '7_Plan_vs_Actual.py')
	app.radio(key='period').set_value(period).run()

	assert_clean(app)


@pytest.mark.parametrize('takehome', [False, True])
def test_plan_vs_actual_takehome_toggle(takehome):
	app = run(WEB_ROOT / 'pages' / '7_Plan_vs_Actual.py')
	app.toggle(key='takehome').set_value(takehome).run()

	assert_clean(app)
	assert len(app.dataframe) >= 1


@pytest.mark.parametrize('basis', ['Whole period', 'Expected by now'])
def test_plan_vs_actual_pacing_basis(basis):
	"""The current month is still running, so both comparison bases are on offer."""
	app = run(WEB_ROOT / 'pages' / '7_Plan_vs_Actual.py')
	app.radio(key='period').set_value('This month').run()
	app.radio(key='basis').set_value(basis).run()

	assert_clean(app)


def test_plan_vs_actual_hides_pacing_for_a_finished_period():
	"""A window wholly in the past has no 'by now' to pace against."""
	app = run(WEB_ROOT / 'pages' / '7_Plan_vs_Actual.py')
	app.radio(key='period').set_value('Previous month').run()

	assert_clean(app)
	assert not [r for r in app.radio if r.key == 'basis']


TRENDS = 'pages/8_Trends.py'


@pytest.mark.parametrize('period', ['Last 6 months', 'Last 24 months', 'Custom range'])
def test_trends_periods(period):
	app = run(WEB_ROOT / TRENDS)
	app.radio(key='period').set_value(period).run()

	assert_clean(app)


@pytest.mark.parametrize('grouping', ['Budget', 'Category', 'Account'])
def test_trends_spending_grouping(grouping):
	app = run(WEB_ROOT / TRENDS)
	app.radio(key='grouping').set_value(grouping).run()

	assert_clean(app)


@pytest.mark.parametrize('key', ['spending_basis', 'income_basis'])
@pytest.mark.parametrize('basis', ['Amounts', 'Share of month'])
def test_trends_amount_and_share(key, basis):
	app = run(WEB_ROOT / TRENDS)
	app.radio(key=key).set_value(basis).run()

	assert_clean(app)


def test_trends_balance_selection_can_be_emptied():
	app = run(WEB_ROOT / TRENDS)
	app.multiselect[0].set_value([]).run()

	assert_clean(app)
	assert any('Pick a budget' in i.value for i in app.info)


def test_trends_needs_more_than_one_month():
	"""A single-month custom range is not a trend, and says so instead of drawing a line."""
	app = run(WEB_ROOT / TRENDS)
	app.radio(key='period').set_value('Custom range').run()
	app.date_input(key='period_range').set_value(
		(pd.Timestamp('2025-06-02'), pd.Timestamp('2025-06-20'))
	).run()

	assert_clean(app)
	assert any('at least two months' in i.value for i in app.info)
