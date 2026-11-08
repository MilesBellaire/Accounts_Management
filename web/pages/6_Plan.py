import bootstrap

bootstrap.page('Plan')

import streamlit as st

import format as fmt
from logic import plan

st.caption(
	'Where money *should* go, given the configured incomes and budgets — as opposed to the '
	'Dashboard, which shows where it actually went.'
)


@st.cache_data(show_spinner=False)
def timeline(takehome):
	return plan.timeline_table(takehome)


@st.cache_data(show_spinner=False)
def percentages(takehome):
	return plan.percentage_table(takehome)


takehome = st.toggle(
	'Take-home only',
	help='Fold taxes and 401k out of salary instead of showing them as budgets',
)

TIMELINE_COLUMNS = {
	'Name': st.column_config.TextColumn('Name', width='medium'),
	'Percentage': fmt.percent_column('Share'),
	'Per Day': fmt.money_column('Per day'),
	'Per Week': fmt.money_column('Per week'),
	'Per Month': fmt.money_column('Per month'),
	'Per Year': fmt.money_column('Per year'),
	'Per 5 Years': fmt.money_column('Per 5 years'),
}


def allocation_columns(result):
	"""Column config for the allocation table, whose income columns vary."""
	columns = {
		'Name': st.column_config.TextColumn('Name', width='medium'),
		'Percentage': fmt.percent_column('Share'),
		'Per Month': fmt.money_column('Per month'),
	}
	for column in result.table.columns:
		if column.endswith(' %'):
			columns[column] = fmt.percent_column(fmt.pretty(column[:-2]) + ' share')
		elif column.endswith(' $'):
			columns[column] = fmt.money_column(fmt.pretty(column[:-2]) + ' amount')
	return columns


def summary_row(values, labels):
	columns = st.columns(len(labels))
	for column, label in zip(columns, labels):
		value = values.get(label, 0)
		with column:
			st.metric(label, fmt.percent(value) if label == 'Percentage' else fmt.money(value))


def section_table(section, result, columns):
	rows = section.rows.drop(columns=[result.group_column]).copy()
	rows['Name'] = fmt.pretty_series(rows['Name'])
	st.dataframe(rows, hide_index=True, width='stretch', column_config=columns)


def render_sections(result, columns, headline):
	"""One block per group: its subtotals, then its rows."""
	for warning in result.warnings:
		st.warning(warning)

	st.markdown('#### All expenses')
	st.caption('Every budget added up. Income is listed separately below, since it funds all of this.')
	summary_row(result.expense_totals, headline)

	for section in result.sections():
		st.divider()
		st.markdown(f'#### {fmt.pretty(section.name)}')
		summary_row(section.subtotals, headline)
		section_table(section, result, columns)


timeline_tab, allocation_tab = st.tabs(['Over time', 'By income'])

with timeline_tab:
	result = timeline(takehome)
	render_sections(result, TIMELINE_COLUMNS, ['Percentage', 'Per Month', 'Per Year'])

	st.divider()
	st.subheader('Monthly plan')

	# Income and expenses are two different things on one scale, so they get their own charts
	# rather than being mixed into a single ranking.
	st.markdown('**Income**')
	income = result.income[result.income['Per Month'] > 0]
	if income.empty:
		st.info('No income configured.')
	else:
		st.plotly_chart(
			fmt.horizontal_bars(income, 'Name', 'Per Month'),
			width='stretch',
		)

	st.markdown('**Expenses**')
	expenses = result.expenses[result.expenses['Per Month'] > 0]
	if expenses.empty:
		st.info('No budgets configured.')
	else:
		st.plotly_chart(
			fmt.horizontal_bars(expenses, 'Name', 'Per Month', color_column='Category'),
			width='stretch',
		)

with allocation_tab:
	result = percentages(takehome)
	render_sections(result, allocation_columns(result), ['Percentage', 'Per Month'])

	st.caption(
		'Each "<income> share" column is the fraction of that income which funds the budget on '
		'this row. The solver keeps every income fully allocated and every budget fully funded.'
	)
