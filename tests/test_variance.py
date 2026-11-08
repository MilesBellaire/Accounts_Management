"""Plan against actual.

The join is exercised with made-up frames so the classification and the pro-rating can be
checked against known numbers; the report itself is then run over the real database to check
it holds together on real shapes.
"""

import pandas as pd
import pytest

from logic import variance


def targets(**per_month):
	return pd.DataFrame({
		'name': list(per_month),
		'category': ['living'] * len(per_month),
		'per_month': list(per_month.values()),
	})


def actuals(**amounts):
	return pd.DataFrame({
		'name': list(amounts),
		'account': ['checking'] * len(amounts),
		'actual': list(amounts.values()),
	})


def rows_by_name(rows):
	return rows.set_index('name')


# --- Window length -----------------------------------------------------------------------

def test_months_between_a_calendar_month_is_about_one():
	assert variance.months_between('2026-03-01', '2026-04-01') == pytest.approx(1, abs=0.02)


def test_months_between_a_year_is_twelve():
	assert variance.months_between('2026-01-01', '2027-01-01') == pytest.approx(12, abs=0.02)


def test_months_between_is_never_negative():
	assert variance.months_between('2026-04-01', '2026-03-01') == 0


# --- Classification ----------------------------------------------------------------------

def test_spending_under_target_is_under():
	rows = variance.build_rows(targets(gas=100), actuals(gas=50), 1, 1)

	assert rows_by_name(rows).loc['gas', 'status'] == 'under'


def test_spending_over_target_is_over():
	rows = variance.build_rows(targets(gas=100), actuals(gas=140), 1, 1)
	gas = rows_by_name(rows).loc['gas']

	assert gas['status'] == 'over'
	assert gas['variance'] == -40


def test_spending_just_short_of_target_is_near():
	rows = variance.build_rows(targets(gas=100), actuals(gas=95), 1, 1)

	assert rows_by_name(rows).loc['gas', 'status'] == 'near'


def test_target_exactly_met_is_near_not_over():
	rows = variance.build_rows(targets(gas=100), actuals(gas=100), 1, 1)

	assert rows_by_name(rows).loc['gas', 'status'] == 'near'


def test_spending_with_no_plan_is_unplanned():
	"""The point of the outer join: a budget the plan does not fund still shows its spending."""
	rows = variance.build_rows(targets(gas=100), actuals(gas=10, mystery=60), 1, 1)
	mystery = rows_by_name(rows).loc['mystery']

	assert mystery['status'] == variance.UNPLANNED
	assert mystery['actual'] == 60
	assert mystery['category'] == variance.UNPLANNED
	assert pd.isna(mystery['used'])


def test_a_budget_with_no_plan_and_no_spending_is_dropped():
	rows = variance.build_rows(targets(gas=0), actuals(gas=0), 1, 1)

	assert rows.empty


def test_a_planned_budget_with_no_spending_is_kept():
	rows = variance.build_rows(targets(gas=100), actuals(), 1, 1)
	gas = rows_by_name(rows).loc['gas']

	assert gas['actual'] == 0
	assert gas['variance'] == 100


# --- Pro-rating --------------------------------------------------------------------------

def test_target_scales_with_the_length_of_the_window():
	rows = variance.build_rows(targets(gas=100), actuals(gas=0), 3, 3)

	assert rows_by_name(rows).loc['gas', 'target'] == 300


def test_expected_follows_elapsed_time_not_the_whole_window():
	"""Half way through a month, only half the target is due."""
	rows = variance.build_rows(targets(gas=100), actuals(gas=60), 1, 0.5)
	gas = rows_by_name(rows).loc['gas']

	assert gas['target'] == 100
	assert gas['expected'] == 50
	# Under target for the month, but running at twice the rate it allows.
	assert gas['status'] == 'under'
	assert gas['projected'] == 120


def test_projection_of_a_finished_window_is_what_was_spent():
	rows = variance.build_rows(targets(gas=100), actuals(gas=80), 1, 1)
	gas = rows_by_name(rows).loc['gas']

	assert gas['projected'] == gas['actual']


def test_nothing_elapsed_does_not_divide_by_zero():
	rows = variance.build_rows(targets(gas=100), actuals(gas=0), 1, 0)

	assert rows_by_name(rows).loc['gas', 'projected'] == 0


# --- Shape -------------------------------------------------------------------------------

def test_rows_are_ordered_most_overspent_first():
	rows = variance.build_rows(
		targets(gas=100, food=100, rent=100),
		actuals(gas=10, food=300, rent=100),
		1, 1,
	)

	assert rows['name'].tolist() == ['food', 'rent', 'gas']


def test_take_home_drops_the_budgets_the_plan_folded_out():
	external = variance.shared_logic.EXTERNAL_BUDGETS[0]

	kept = variance.build_rows(targets(gas=100), actuals(**{external: 500}), 1, 1, takehome=False)
	dropped = variance.build_rows(targets(gas=100), actuals(**{external: 500}), 1, 1, takehome=True)

	assert external in kept['name'].tolist()
	assert external not in dropped['name'].tolist()


def test_build_rows_returns_the_declared_columns():
	rows = variance.build_rows(targets(gas=100), actuals(gas=50), 1, 1)

	assert rows.columns.tolist() == variance.ROW_COLUMNS


# --- Report ------------------------------------------------------------------------------

def test_report_holds_together_on_the_real_database():
	report = variance.variance_report('2000-01-01', '2100-01-01')

	assert report.rows.columns.tolist() == variance.ROW_COLUMNS
	assert set(report.rows['status']) <= set(variance.STATUS_ORDER)
	# The identity every reading of the table depends on.
	assert (report.rows['variance'] - (report.rows['target'] - report.rows['actual'])).abs().max() < 0.02


def test_report_totals_match_the_rows():
	report = variance.variance_report('2000-01-01', '2100-01-01')

	assert report.totals['actual'] == pytest.approx(report.rows['actual'].sum(), abs=0.02)
	assert report.totals['target'] == pytest.approx(report.rows['target'].sum(), abs=0.02)


def test_a_window_ending_in_the_future_is_in_progress():
	report = variance.variance_report('2000-01-01', '2100-01-01')

	assert report.in_progress
	assert report.elapsed_months < report.months


def test_a_window_wholly_in_the_past_is_not_in_progress():
	report = variance.variance_report('2000-01-01', '2000-04-01')

	assert not report.in_progress
	assert report.elapsed_months == pytest.approx(report.months)


def test_category_rollup_totals_match_the_rows():
	report = variance.variance_report('2000-01-01', '2100-01-01')
	rollup = variance.by_category(report)

	assert rollup['actual'].sum() == pytest.approx(report.rows['actual'].sum(), abs=0.02)
	assert set(rollup['category']) == set(report.rows['category'])


def test_take_home_report_runs():
	report = variance.variance_report('2000-01-01', '2100-01-01', takehome=True)

	assert not report.empty
