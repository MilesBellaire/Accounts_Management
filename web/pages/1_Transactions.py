import bootstrap
from bootstrap import sql

bootstrap.page('Transactions')

import pandas as pd
import streamlit as st

import format as fmt

UNASSIGNED = '—'

budgets = bootstrap.budgets()
incomes = bootstrap.incomes()
accounts = bootstrap.accounts()
statements = bootstrap.statements()


@st.cache_data(show_spinner=False)
def load(**filters):
	return sql.transaction.get(**filters)


# --- Filters -----------------------------------------------------------------------------

with st.sidebar:
	st.subheader('Filters')

	date_range = st.date_input(
		'Date range',
		value=(),
		key='filter_dates',
		help='Leave empty for every transaction',
	)
	search = st.text_input('Description contains', key='filter_search')

	account_name = st.selectbox(
		'Account', ['Any'] + accounts['name'].tolist(), format_func=fmt.pretty, key='filter_account'
	)
	budget_name = st.selectbox(
		'Budget', ['Any'] + budgets['name'].tolist(), format_func=fmt.pretty, key='filter_budget'
	)
	income_name = st.selectbox(
		'Income', ['Any'] + incomes['name'].tolist(), format_func=fmt.pretty, key='filter_income'
	)
	statement_name = st.selectbox(
		'Statement', ['Any'] + statements['name'].tolist(), key='filter_statement'
	)

	transfers = st.selectbox(
		'Transfers',
		['Include', 'Exclude', 'Only transfers'],
		key='filter_transfers',
		help='Transfers move money between your own accounts and are neither income nor spending',
	)

filters = {}

if len(date_range) == 2:
	filters['start_date'] = date_range[0].strftime('%Y-%m-%d')
	filters['end_date'] = (pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
if search:
	filters['search'] = search
if account_name != 'Any':
	filters['account_id'] = bootstrap.name_to_id(accounts, account_name)
if budget_name != 'Any':
	filters['budget_id'] = bootstrap.name_to_id(budgets, budget_name)
if income_name != 'Any':
	filters['income_id'] = bootstrap.name_to_id(incomes, income_name)
if statement_name != 'Any':
	row = statements[statements['name'] == statement_name]
	filters['statement_id'] = int(row.iloc[0]['id'])
if transfers == 'Exclude':
	filters['is_transfer'] = False
elif transfers == 'Only transfers':
	filters['is_transfer'] = True

transactions = load(**filters)

if transactions.empty:
	st.info('No transactions match these filters.')
	st.stop()

# --- Summary -----------------------------------------------------------------------------

debits = transactions.loc[transactions['debit_or_credit'] == '-', 'amount'].sum()
credits = transactions.loc[transactions['debit_or_credit'] == '+', 'amount'].sum()
uncategorized = (
	transactions['budget_id'].isna() & transactions['income_id'].isna()
).sum() + (transactions[['budget_id', 'income_id']] == -1).any(axis=1).sum()

a, b, c, d = st.columns(4)
a.metric('Transactions', f'{len(transactions):,}')
b.metric('Money in', fmt.money(credits))
c.metric('Money out', fmt.money(debits))
d.metric('Need a category', f'{uncategorized:,}')

st.divider()

# --- Editable table ----------------------------------------------------------------------

st.caption(
	'Change a budget or income below and press Save. Debits take a budget, credits take an '
	'income; changing a credit rebuilds that transaction\'s income distribution.'
)

display = transactions[[
	'id', 'date', 'description', 'debit_or_credit', 'amount',
	'budget', 'income', 'account', 'statement', 'is_transfer',
]].copy()
display['date'] = pd.to_datetime(display['date'])
display['budget'] = fmt.pretty_series(display['budget']).fillna(UNASSIGNED)
display['income'] = fmt.pretty_series(display['income']).fillna(UNASSIGNED)
display['account'] = fmt.pretty_series(display['account'])

# The editor works in pretty labels; these map a choice back to the stored name.
budget_names = fmt.unpretty_map(budgets['name'])
income_names = fmt.unpretty_map(incomes['name'])

edited = st.data_editor(
	display,
	hide_index=True,
	width='stretch',
	height=560,
	key='transaction_editor',
	disabled=['id', 'date', 'debit_or_credit', 'amount', 'account', 'statement', 'is_transfer'],
	column_config={
		'id': st.column_config.NumberColumn('ID', format='%d', width='small'),
		'date': st.column_config.DateColumn('Date', format='YYYY-MM-DD', width='small'),
		'description': st.column_config.TextColumn('Description', width='large'),
		'debit_or_credit': st.column_config.TextColumn('+/-', width='small'),
		'amount': fmt.money_column('Amount'),
		'budget': st.column_config.SelectboxColumn(
			'Budget', options=[UNASSIGNED] + fmt.pretty_list(budgets['name'])
		),
		'income': st.column_config.SelectboxColumn(
			'Income', options=[UNASSIGNED] + fmt.pretty_list(incomes['name'])
		),
		'account': st.column_config.TextColumn('Account', width='small'),
		'statement': st.column_config.TextColumn('Statement', width='medium'),
		'is_transfer': st.column_config.CheckboxColumn('Transfer', width='small'),
	},
)

changes = edited.compare(display) if not edited.equals(display) else pd.DataFrame()

if changes.empty:
	st.button('Save changes', disabled=True)
else:
	changed_rows = display.loc[changes.index]
	st.warning(f'{len(changed_rows)} row(s) changed.')

	if st.button('Save changes', type='primary'):
		saved = 0
		for index in changes.index:
			before = display.loc[index]
			after = edited.loc[index]
			transact_id = int(before['id'])

			if after['budget'] != before['budget']:
				stored = budget_names.get(after['budget'])
				sql.transaction.update_budget(transact_id, bootstrap.name_to_id(budgets, stored))
				saved += 1
			if after['income'] != before['income']:
				stored = income_names.get(after['income'])
				sql.transaction.update_income(transact_id, bootstrap.name_to_id(incomes, stored))
				saved += 1
			if after['description'] != before['description']:
				sql.transaction.update_description(transact_id, after['description'])
				saved += 1

		bootstrap.clear_caches()
		st.success(f'Saved {saved} change(s).')
		st.rerun()
