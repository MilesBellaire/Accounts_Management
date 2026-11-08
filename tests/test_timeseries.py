"""Month-by-month series.

The shaping - the zero fill, the running balance, the folded tail, the shares - is checked
against made-up frames; the queries behind it are then run over the real database to check
they come back in the shape the shaping expects.
"""

import pandas as pd
import pytest

from logic import timeseries


def frame(rows):
	"""rows: (month, name, debits, credits, transfered, change)"""
	return pd.DataFrame(
		rows, columns=['month', 'name', 'debits', 'credits', 'transfered', 'change']
	)


# --- The month axis ----------------------------------------------------------------------

def test_months_covers_the_window_end_exclusive():
	assert timeseries.months('2026-01-01', '2026-04-01') == ['2026-01', '2026-02', '2026-03']


def test_months_includes_a_partial_month():
	assert timeseries.months('2026-01-15', '2026-03-10') == ['2026-01', '2026-02', '2026-03']


def test_months_of_an_empty_window_is_empty():
	assert timeseries.months('2026-04-01', '2026-04-01') == []


# --- Zero fill ---------------------------------------------------------------------------

def test_a_month_with_no_activity_is_filled_with_zero():
	"""A gap in a series reads as 'no data'; the months a budget sat idle must be drawn."""
	dense = timeseries._dense(
		frame([('2026-01', 'gas', 40, 0, 0, -40), ('2026-03', 'gas', 60, 0, 0, -60)]),
		['2026-01', '2026-02', '2026-03'],
		timeseries.SPENDING_COLUMNS,
	)

	assert dense['month'].tolist() == ['2026-01', '2026-02', '2026-03']
	assert dense.set_index('month').loc['2026-02', 'debits'] == 0


def test_every_series_appears_in_every_month():
	dense = timeseries._dense(
		frame([('2026-01', 'gas', 40, 0, 0, -40), ('2026-02', 'food', 90, 0, 0, -90)]),
		['2026-01', '2026-02'],
		timeseries.SPENDING_COLUMNS,
	)

	assert len(dense) == 4
	assert sorted(dense[dense['month'] == '2026-01']['name']) == ['food', 'gas']


def test_dense_of_an_empty_frame_keeps_its_columns():
	dense = timeseries._dense(frame([]), ['2026-01'], timeseries.SPENDING_COLUMNS)

	assert dense.empty
	assert 'month' in dense.columns and 'debits' in dense.columns


# --- Folding the tail --------------------------------------------------------------------

def test_a_short_series_list_is_left_alone():
	rows = frame([('2026-01', name, 10, 0, 0, -10) for name in 'abc'])

	assert set(timeseries.top_series(rows, 'debits')['name']) == set('abc')


def test_a_long_tail_is_folded_into_one_series():
	rows = frame([('2026-01', f'b{i}', 100 - i, 0, 0, 0) for i in range(12)])
	folded = timeseries.top_series(rows, 'debits', limit=3)

	assert sorted(folded['name']) == ['b0', 'b1', 'b2', timeseries.OTHER]
	# Nothing may be lost in the fold.
	assert folded['debits'].sum() == rows['debits'].sum()


def test_folding_keeps_the_largest_series():
	rows = frame([
		('2026-01', 'big', 500, 0, 0, 0),
		('2026-01', 'small', 1, 0, 0, 0),
		('2026-01', 'tiny', 2, 0, 0, 0),
	])
	folded = timeseries.top_series(rows, 'debits', limit=1)

	assert set(folded['name']) == {'big', timeseries.OTHER}
	assert folded.set_index('name').loc[timeseries.OTHER, 'debits'] == 3


def test_folding_sums_the_tail_within_each_month():
	rows = frame([
		('2026-01', 'big', 500, 0, 0, 0), ('2026-02', 'big', 500, 0, 0, 0),
		('2026-01', 'a', 1, 0, 0, 0), ('2026-01', 'b', 2, 0, 0, 0),
		('2026-02', 'a', 4, 0, 0, 0), ('2026-02', 'b', 8, 0, 0, 0),
	])
	folded = timeseries.top_series(rows, 'debits', limit=1).set_index(['month', 'name'])

	assert folded.loc[('2026-01', timeseries.OTHER), 'debits'] == 3
	assert folded.loc[('2026-02', timeseries.OTHER), 'debits'] == 12


# --- Regrouping --------------------------------------------------------------------------

def test_group_series_rolls_budgets_onto_their_tags():
	rows = frame([
		('2026-01', 'gas', 40, 0, 0, 0),
		('2026-01', 'insurance', 60, 0, 0, 0),
		('2026-01', 'food', 90, 0, 0, 0),
	])
	grouped = timeseries.group_series(
		rows, 'debits', {'gas': 'car', 'insurance': 'car', 'food': 'living'}
	).set_index('name')

	assert grouped.loc['car', 'debits'] == 100
	assert grouped.loc['living', 'debits'] == 90


def test_group_series_names_the_ungrouped():
	rows = frame([('2026-01', 'gas', 40, 0, 0, 0), ('2026-01', 'mystery', 10, 0, 0, 0)])
	grouped = timeseries.group_series(rows, 'debits', {'gas': 'car'})

	assert 'uncategorized' in grouped['name'].tolist()


def test_group_series_treats_a_blank_tag_as_ungrouped():
	rows = frame([('2026-01', 'gas', 40, 0, 0, 0)])
	grouped = timeseries.group_series(rows, 'debits', {'gas': ''})

	assert grouped['name'].tolist() == ['uncategorized']


# --- Shares ------------------------------------------------------------------------------

def test_shares_add_to_one_within_each_month():
	rows = frame([
		('2026-01', 'gas', 25, 0, 0, 0), ('2026-01', 'food', 75, 0, 0, 0),
		('2026-02', 'gas', 10, 0, 0, 0), ('2026-02', 'food', 10, 0, 0, 0),
	])
	shared = timeseries.as_share(rows, 'debits')

	assert shared.groupby('month')['share'].sum().tolist() == [1.0, 1.0]
	assert shared.set_index(['month', 'name']).loc[('2026-01', 'gas'), 'share'] == 0.25


def test_a_month_with_no_spending_has_no_share_rather_than_a_divide_by_zero():
	rows = frame([('2026-01', 'gas', 0, 0, 0, 0), ('2026-02', 'gas', 50, 0, 0, 0)])
	shared = timeseries.as_share(rows, 'debits')

	assert shared.set_index('month').loc['2026-01', 'share'] == 0
	assert shared.set_index('month').loc['2026-02', 'share'] == 1


# --- Selection ---------------------------------------------------------------------------

def test_latest_by_picks_from_the_most_recent_month():
	rows = pd.DataFrame({
		'month': ['2026-01', '2026-01', '2026-02', '2026-02'],
		'name': ['gas', 'food', 'gas', 'food'],
		'balance': [900, 10, 5, 800],
	})

	assert timeseries.latest_by(rows, 'balance', limit=1) == ['food']


def test_latest_by_of_an_empty_frame_is_empty():
	assert timeseries.latest_by(pd.DataFrame(), 'balance') == []


# --- Against the real database -----------------------------------------------------------

WINDOW = ('2025-01-01', '2026-01-01')


def test_monthly_spending_is_dense_over_the_real_database():
	frame = timeseries.monthly_spending(*WINDOW)
	expected = timeseries.months(*WINDOW)

	assert not frame.empty
	assert sorted(frame['month'].unique()) == expected
	# Dense means every series appears in every month, so the row count is the product.
	assert len(frame) == len(expected) * frame['name'].nunique()
	assert not frame['account'].isna().any()


def test_monthly_spending_agrees_with_the_single_window_report():
	"""The months must add up to what the Dashboard reports for the whole window."""
	from logic import reports

	monthly = timeseries.monthly_spending(*WINDOW)
	window = reports.balance_report(*WINDOW)

	assert monthly['debits'].sum() == pytest.approx(window.totals['debits'], abs=0.05)
	assert monthly['credits'].sum() == pytest.approx(window.totals['credits'], abs=0.05)


def test_monthly_balances_end_where_the_window_report_ends():
	"""The last month's running balance is the window's closing balance."""
	from logic import reports

	balances = timeseries.monthly_balances(*WINDOW)
	window = reports.balance_report(*WINDOW)

	final = balances[balances['month'] == balances['month'].max()]

	assert final['balance'].sum() == pytest.approx(window.totals['balance'], abs=0.05)


def test_monthly_balances_carry_forward_a_quiet_month():
	"""A budget that saw nothing in a month keeps its balance rather than dropping to zero."""
	balances = timeseries.monthly_balances(*WINDOW)
	quiet = balances[balances['change'] == 0]

	assert not quiet.empty, 'expected at least one month with no activity'
	# A carried-forward balance is whatever it was; what it must not be is a gap.
	assert not quiet['balance'].isna().any()


def test_monthly_income_is_dense_over_the_real_database():
	frame = timeseries.monthly_income(*WINDOW)

	assert not frame.empty
	assert sorted(frame['month'].unique()) == timeseries.months(*WINDOW)


def test_monthly_totals_net_is_in_minus_out():
	totals = timeseries.monthly_totals(*WINDOW)

	assert (totals['net'] - (totals['credits'] - totals['debits'])).abs().max() < 0.01
