import bootstrap

bootstrap.page('Trends')

import pandas as pd
import streamlit as st

import format as fmt
from logic import timeseries

st.caption(
	'How spending, income and balances have moved month to month. The Dashboard and Plan vs '
	'Actual both look at one period; this is the same figures across many.'
)


@st.cache_data(show_spinner=False)
def spending(start_date, end_date):
	return timeseries.monthly_spending(start_date, end_date)


@st.cache_data(show_spinner=False)
def income(start_date, end_date):
	return timeseries.monthly_income(start_date, end_date)


@st.cache_data(show_spinner=False)
def balances(start_date, end_date):
	return timeseries.monthly_balances(start_date, end_date)


@st.cache_data(show_spinner=False)
def totals(start_date, end_date):
	return timeseries.monthly_totals(start_date, end_date)


start_date, end_date = bootstrap.period_picker(
	['Last 6 months', 'Last 12 months', 'Last 24 months', 'Custom range']
)

months = timeseries.months(start_date, end_date)

if len(months) < 2:
	st.info('Pick a period covering at least two months — one month is not a trend.')
	st.stop()


def table_view(frame, value_column, label, percent=False):
	"""Every chart here ships with its own table.

	Two of the series colors sit under 3:1 against the light surface, and a readable table is
	the relief that makes that legible anyway - as well as being the better way to read an
	exact figure off a stack.
	"""
	pivot = (
		frame.pivot_table(index=timeseries.NAME, columns=timeseries.MONTH, values=value_column)
		.fillna(0.0)
		.round(2)
		.reset_index()
	)
	pivot[timeseries.NAME] = fmt.pretty_series(pivot[timeseries.NAME])

	column = fmt.percent_column if percent else fmt.money_column
	config = {str(c): column(str(c)) for c in pivot.columns if c != timeseries.NAME}
	config[timeseries.NAME] = st.column_config.TextColumn(label, width='medium', pinned=True)

	with st.expander('Table'):
		st.dataframe(pivot, hide_index=True, width='stretch', column_config=config)


def amount_or_share(key):
	"""Amounts answer 'how much', shares answer 'is this taking a bigger slice'."""
	return st.radio(
		'Show', ['Amounts', 'Share of month'], horizontal=True, key=key,
		help='A share is of that month’s total, so it moves when overall income moves.',
	)


# --- Money in and out --------------------------------------------------------------------

st.subheader('Money in and out')

monthly = totals(start_date, end_date)

average_in, average_out, average_net = st.columns(3)
with average_in:
	fmt.stat('Average in', fmt.money(monthly['credits'].mean()), help='Per month over this period')
with average_out:
	fmt.stat('Average out', fmt.money(monthly['debits'].mean()), help='Per month over this period')
with average_net:
	net = monthly['net'].mean()
	fmt.stat('Average net', fmt.money(net), delta=fmt.money(net))

# Two measures on one scale, so one chart with one axis rather than two stacked on each other.
in_and_out = pd.concat([
	monthly[[timeseries.MONTH, 'credits']].rename(columns={'credits': 'amount'}).assign(name='in'),
	monthly[[timeseries.MONTH, 'debits']].rename(columns={'debits': 'amount'}).assign(name='out'),
])

st.plotly_chart(
	fmt.lines(in_and_out, timeseries.MONTH, 'amount', 'name'),
	width='stretch',
)
table_view(in_and_out, 'amount', 'Flow')

st.divider()

spending_tab, income_tab, balance_tab = st.tabs(['Spending', 'Income', 'Balances'])

# --- Spending ----------------------------------------------------------------------------

with spending_tab:
	frame = spending(start_date, end_date)

	if frame.empty:
		st.info('No spending in this period.')
	else:
		grouping = st.radio(
			'Group by', ['Budget', 'Category', 'Account'], horizontal=True, key='grouping'
		)

		if grouping == 'Budget':
			# More budgets than a categorical palette has slots, so the tail folds into one.
			series = timeseries.top_series(frame, 'debits')
		else:
			budgets = bootstrap.budgets()
			mapping = (
				dict(zip(budgets['name'], budgets['tags'])) if grouping == 'Category'
				else dict(zip(frame['name'], frame['account']))
			)
			series = timeseries.top_series(
				timeseries.group_series(frame, 'debits', mapping), 'debits'
			)

		basis = amount_or_share('spending_basis')
		percent = basis == 'Share of month'

		if percent:
			series = timeseries.as_share(series, 'debits')

		column = 'share' if percent else 'debits'

		st.plotly_chart(
			fmt.stacked_columns(series, timeseries.MONTH, column, 'name', percent=percent),
			width='stretch',
		)
		table_view(series, column, grouping, percent=percent)

# --- Income ------------------------------------------------------------------------------

with income_tab:
	frame = income(start_date, end_date)

	if frame.empty:
		st.info('No income in this period.')
	else:
		series = timeseries.top_series(frame, 'amount')

		basis = amount_or_share('income_basis')
		percent = basis == 'Share of month'

		if percent:
			series = timeseries.as_share(series, 'amount')

		column = 'share' if percent else 'amount'

		st.plotly_chart(
			fmt.stacked_columns(series, timeseries.MONTH, column, 'name', percent=percent),
			width='stretch',
		)
		table_view(series, column, 'Income', percent=percent)

# --- Balances ----------------------------------------------------------------------------

with balance_tab:
	frame = balances(start_date, end_date)

	if frame.empty:
		st.info('No balances in this period.')
	else:
		st.caption(
			'The running balance of each budget at the end of each month. Lines are for '
			'telling a few series apart, so this shows a handful at a time.'
		)

		options = sorted(frame['name'].unique())
		chosen = st.multiselect(
			'Budgets',
			options,
			default=timeseries.latest_by(frame, 'balance'),
			format_func=fmt.pretty,
			max_selections=6,
		)

		if not chosen:
			st.info('Pick a budget to chart.')
		else:
			shown = frame[frame['name'].isin(chosen)]
			st.plotly_chart(
				fmt.lines(shown, timeseries.MONTH, 'balance', 'name'),
				width='stretch',
			)
			table_view(shown, 'balance', 'Budget')
