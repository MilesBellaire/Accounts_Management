"""The Plan page splits each table into one section per category/account with subtotals."""

import pytest

from logic import plan

TABLES = [('timeline', plan.timeline_table), ('percentage', plan.percentage_table)]


@pytest.fixture(params=[False, True], ids=['gross', 'takehome'])
def takehome(request):
	return request.param


@pytest.mark.parametrize('name, build', TABLES, ids=[n for n, _ in TABLES])
def test_sections_cover_every_row(name, build, takehome):
	result = build(takehome)
	sections = result.sections()

	assert sections
	assert sum(len(s.rows) for s in sections) == len(result.table)


@pytest.mark.parametrize('name, build', TABLES, ids=[n for n, _ in TABLES])
def test_subtotals_sum_to_totals(name, build, takehome):
	result = build(takehome)
	summed = sum(s.subtotals for s in result.sections())

	for column in result.value_columns:
		assert summed[column] == pytest.approx(result.totals[column]), column


@pytest.mark.parametrize('name, build', TABLES, ids=[n for n, _ in TABLES])
def test_sections_are_ordered_largest_first(name, build, takehome):
	result = build(takehome)
	monthly = [s.subtotals['Per Month'] for s in result.sections()]

	assert monthly == sorted(monthly, reverse=True)


@pytest.mark.parametrize('name, build', TABLES, ids=[n for n, _ in TABLES])
def test_section_names_are_unique(name, build, takehome):
	names = [s.name for s in build(takehome).sections()]

	assert len(names) == len(set(names))


def test_takehome_drops_external_budgets():
	"""taxes and 401k are folded into salary in the take-home view."""
	gross = {s.name for s in plan.timeline_table(False).sections()}
	net = {s.name for s in plan.timeline_table(True).sections()}

	assert net <= gross
	assert 'taxes' not in plan.timeline_table(True).table['Name'].tolist()
	assert '401k' not in plan.timeline_table(True).table['Name'].tolist()


@pytest.mark.parametrize('name, build', TABLES, ids=[n for n, _ in TABLES])
def test_expense_totals_exclude_income(name, build, takehome):
	"""Income funds the budgets, so the headline total must not add both together."""
	result = build(takehome)

	assert not result.income.empty
	assert (result.expenses[result.group_column] != plan.INCOME_GROUP).all()

	for column in result.value_columns:
		assert result.expense_totals[column] + result.income_totals[column] == pytest.approx(
			result.totals[column]
		)
		assert result.expense_totals[column] != pytest.approx(result.totals[column])


@pytest.mark.parametrize('name, build', TABLES, ids=[n for n, _ in TABLES])
def test_expenses_and_income_partition_the_table(name, build, takehome):
	result = build(takehome)

	assert len(result.expenses) + len(result.income) == len(result.table)
