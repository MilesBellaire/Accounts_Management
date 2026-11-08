import bootstrap

bootstrap.page('Dashboard')

import streamlit as st

import format as fmt
from logic import reports


@st.cache_data(show_spinner=False)
def balance_report(start_date, end_date):
	return reports.balance_report(start_date, end_date)


@st.cache_data(show_spinner=False)
def account_diff():
	return reports.account_diff()


# --- Period ------------------------------------------------------------------------------

start_date, end_date = bootstrap.period_picker(
	['All time', 'This month', 'Previous month', 'Month', 'Custom range']
)

report = balance_report(start_date, end_date)

if report.empty:
	st.info('No transactions in this period.')
	st.stop()

# --- Headline numbers --------------------------------------------------------------------

totals = report.totals
left, mid_left, mid_right, right = st.columns(4)

with left:
	fmt.stat('Balance', fmt.money(totals['balance']), help='Across every budget at the end of the period')
with mid_left:
	fmt.stat('Money in', fmt.money(totals['credits']), help='Income allocated to budgets in this period')
with mid_right:
	fmt.stat('Money out', fmt.money(totals['debits']), help='Spending in this period')
with right:
	fmt.stat(
		'Net change',
		fmt.money(totals['change']),
		delta=fmt.money(totals['change']),
		help='Credits minus debits, including transfers between budgets',
	)

st.divider()

# --- Balances ----------------------------------------------------------------------------

by_budget = report.by_budget[report.by_budget['balance'] != 0]
by_account = report.by_account


def for_display(df, *columns):
	"""Stored names are lowercase with underscores; tables show the pretty form."""
	shown = df.copy()
	for column in columns:
		if column in shown:
			shown[column] = fmt.pretty_series(shown[column])
	return shown

chart_left, chart_right = st.columns([2, 1])

with chart_left:
	st.subheader('Balance by budget')
	st.caption('Colored by the account the budget draws from.')
	st.plotly_chart(
		fmt.horizontal_bars(by_budget, 'name', 'balance', color_column='account'),
		width='stretch',
	)

with chart_right:
	st.subheader('Balance by account')
	st.caption('')
	st.plotly_chart(
		fmt.horizontal_bars(by_account, 'account', 'balance', height=340),
		width='stretch',
	)

	st.subheader('Reconciliation')
	st.caption('System-tracked budget balances against the real account balances.')
	diff, diff_totals = account_diff()
	st.dataframe(
		for_display(diff, 'account'),
		hide_index=True,
		width='stretch',
		column_config={
			'account': 'Account',
			'budget_balance': fmt.money_column('Budgets'),
			'account_balance': fmt.money_column('Accounts'),
			'diff': fmt.money_column('Diff', help='Non-zero means transactions are missing or miscategorised'),
		},
	)
	st.caption(f'Total difference: {fmt.money(diff_totals["diff"])}')

st.divider()

# --- Detail ------------------------------------------------------------------------------

st.subheader('Detail')

tab_budget, tab_account = st.tabs(['By budget', 'By account'])

balance_columns = {
	'account': 'Account',
	'name': 'Budget',
	'initial_balance': fmt.money_column('Opening'),
	'debits': fmt.money_column('Out'),
	'credits': fmt.money_column('In'),
	'transfered': fmt.money_column('Transferred'),
	'change': fmt.money_column('Change'),
	'balance': fmt.money_column('Balance'),
}

with tab_budget:
	st.dataframe(
		for_display(report.by_budget, 'account', 'name'),
		hide_index=True,
		width='stretch',
		column_config=balance_columns,
	)
	st.caption(
		'  •  '.join(f'{label}: {fmt.money(totals[key])}' for key, label in [
			('initial_balance', 'Opening'), ('debits', 'Out'), ('credits', 'In'),
			('transfered', 'Transferred'), ('change', 'Change'), ('balance', 'Balance'),
		])
	)

with tab_account:
	st.dataframe(
		for_display(by_account, 'account'),
		hide_index=True,
		width='stretch',
		column_config=balance_columns,
	)
