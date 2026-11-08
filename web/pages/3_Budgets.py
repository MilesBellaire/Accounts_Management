import bootstrap
from bootstrap import sql

bootstrap.page('Budgets')

import pandas as pd
import streamlit as st

import format as fmt
from logic import equations

UNIT_HELP = {
	'$': 'A flat amount per month',
	'%ov': 'A percentage of overall income',
	'%lo-': 'A percentage of what is left after fixed expenses, capped',
	'%lo+': 'A percentage of what is left, absorbing what the capped ones give up',
	'eq': 'An amount computed from an equation',
}

budgets = bootstrap.budgets()
units = bootstrap.budget_units()
tracking_types = bootstrap.tracking_types()
accounts = bootstrap.accounts()
incomes = bootstrap.incomes()

view_tab, add_tab, edit_tab, remove_tab = st.tabs(['View', 'Add', 'Edit', 'Remove'])


def unit_options():
	return units['abv'].tolist()


def budgets_for_income(income_name):
	row = incomes[incomes['name'] == income_name]
	return [] if row.empty else [b for b in row.iloc[0]['budgets'].split(', ') if b]


def incomes_feeding(budget_name):
	return [
		income['name'] for _, income in incomes.iterrows()
		if budget_name in [b for b in income['budgets'].split(', ') if b]
	]


def equation_input(label, value='', key=None):
	equation = st.text_input(
		label,
		value=value or '',
		key=key,
		help='Format: [self] + [variable] * [constant].  Operators: + - * /',
	)
	st.caption('Available variables: ' + ', '.join(f'`[{v}]`' for v in equations.available_variables()))

	if equation:
		error = equations.validate(equation)
		if error:
			st.error(error)
			return equation, False
		st.success(f'Evaluates to {fmt.money(equations.evaluate(equation, 0))} with [self] = 0')
	return equation, True


def value_and_cap(unit, value_default=0.0, cap_default=None, key_prefix=''):
	label = 'Value ($ per month)' if unit in ('$', 'eq') else 'Value (%)'
	value = st.number_input(label, value=float(value_default or 0.0), key=f'{key_prefix}value')

	cap = None
	if unit == '%lo-':
		cap = st.number_input(
			'Cap ($ per month)',
			min_value=0.01,
			value=float(cap_default) if cap_default and not pd.isna(cap_default) else 100.0,
			key=f'{key_prefix}cap',
		)
	return value, cap


# --- View --------------------------------------------------------------------------------

with view_tab:
	if budgets.empty:
		st.info('No budgets yet.')
	else:
		shown = budgets[['name', 'unit', 'value', 'cap', 'equation', 'tags', 'tracking_type', 'account', 'id']].copy()
		shown['name'] = fmt.pretty_series(shown['name'])
		shown['account'] = fmt.pretty_series(shown['account'])
		st.dataframe(
			shown,
			hide_index=True,
			width='stretch',
			column_config={
				'name': 'Name',
				'unit': st.column_config.TextColumn('Unit', width='small'),
				'value': st.column_config.NumberColumn('Value', format='%.2f'),
				'cap': st.column_config.NumberColumn('Cap', format='%.2f'),
				'equation': st.column_config.TextColumn('Equation', width='large'),
				'tags': 'Tags',
				'tracking_type': 'Tracking',
				'account': 'Account',
				'id': st.column_config.NumberColumn('ID', format='%d', width='small'),
			},
		)
		with st.expander('What the units mean'):
			for abv, description in UNIT_HELP.items():
				st.markdown(f'- `{abv}` — {description}')

# --- Add ---------------------------------------------------------------------------------

with add_tab:
	name = st.text_input('Name', key='add_name', help='Lowercase, no spaces')
	unit = st.selectbox('Unit', unit_options(), key='add_unit', help=UNIT_HELP.get('$'))
	st.caption(UNIT_HELP.get(unit, ''))

	value, cap = value_and_cap(unit, key_prefix='add_')

	equation, equation_ok = ('', True)
	if unit == 'eq':
		equation, equation_ok = equation_input('Equation', key='add_equation')

	tracking_type = st.selectbox('Tracking type', tracking_types['name'].tolist(), key='add_tracking')
	account = st.selectbox('Account', accounts['name'].tolist(), key='add_account')
	tags = st.text_input('Tags', key='add_tags')
	attached = st.multiselect(
		'Funded by these incomes', incomes['name'].tolist(), format_func=fmt.pretty, key='add_incomes'
	)

	problems = []
	if not name.strip():
		problems.append('Name is required')
	elif ' ' in name.strip():
		problems.append('Name cannot contain spaces')
	elif name.strip().lower() in budgets['name'].tolist():
		problems.append('A budget with that name already exists')
	if unit == 'eq' and not equation_ok:
		problems.append('Fix the equation')

	for problem in problems:
		st.warning(problem)

	if st.button('Add budget', type='primary', disabled=bool(problems)):
		new_id = sql.budget.insert(
			name.strip().lower(),
			equation or None,
			tags,
			bootstrap.name_to_id(tracking_types, tracking_type),
			int(units[units['abv'] == unit].iloc[0]['id']),
			value,
			cap,
			bootstrap.name_to_id(accounts, account),
		)
		for income_name in attached:
			sql.insert_distribution_budget(bootstrap.name_to_id(incomes, income_name), new_id)

		bootstrap.clear_caches()
		st.success(f'Added {name.strip().lower()}.')
		st.rerun()

# --- Edit --------------------------------------------------------------------------------

with edit_tab:
	if budgets.empty:
		st.info('No budgets to edit.')
	else:
		chosen = st.selectbox(
			'Budget', budgets['name'].tolist(), format_func=fmt.pretty, key='edit_choice'
		)
		row = budgets[budgets['name'] == chosen].iloc[0]

		# Streamlit ignores value=/index= once a key already holds state, so the keys carry the
		# budget id: picking a different budget makes fresh widgets that show its own values.
		k = f'_{int(row["id"])}'

		new_name = st.text_input(
			'Name', value=row['name'], key=f'edit_name{k}',
			help='Stored lowercase with underscores; tables and charts show it prettified',
		)
		new_unit = st.selectbox(
			'Unit', unit_options(), index=unit_options().index(row['unit']), key=f'edit_unit{k}'
		)
		st.caption(UNIT_HELP.get(new_unit, ''))

		new_value, new_cap = value_and_cap(
			new_unit, row['value'], row['cap'], key_prefix=f'edit{k}_'
		)

		new_equation, equation_ok = (row['equation'], True)
		if new_unit == 'eq':
			new_equation, equation_ok = equation_input(
				'Equation', value=row['equation'], key=f'edit_equation{k}'
			)

		new_tracking = st.selectbox(
			'Tracking type',
			tracking_types['name'].tolist(),
			index=tracking_types['name'].tolist().index(row['tracking_type']),
			key=f'edit_tracking{k}',
		)
		new_account = st.selectbox(
			'Account',
			accounts['name'].tolist(),
			index=accounts['name'].tolist().index(row['account']),
			key=f'edit_account{k}',
		)
		new_tags = st.text_input('Tags', value=row['tags'] or '', key=f'edit_tags{k}')

		st.caption(
			'Incomes funding this budget: '
			+ (', '.join(fmt.pretty_list(incomes_feeding(chosen))) or 'none')
			+ ' — change these on the Incomes page.'
		)

		if st.button('Save budget', type='primary', disabled=not equation_ok):
			sql.budget.update(
				int(row['id']),
				new_name.strip().lower(),
				new_equation or None,
				new_tags,
				bootstrap.name_to_id(tracking_types, new_tracking),
				int(units[units['abv'] == new_unit].iloc[0]['id']),
				new_value,
				new_cap,
				bootstrap.name_to_id(accounts, new_account),
			)
			bootstrap.clear_caches()
			st.success(f'Saved {new_name}.')
			st.rerun()

# --- Remove ------------------------------------------------------------------------------

with remove_tab:
	if budgets.empty:
		st.info('No budgets to remove.')
	else:
		chosen = st.selectbox(
			'Budget', budgets['name'].tolist(), format_func=fmt.pretty, key='remove_choice'
		)
		row = budgets[budgets['name'] == chosen].iloc[0]

		st.warning(
			f'Deleting **{chosen}** unassigns its transactions (they become category -1) and '
			'removes it from every income distribution. Balances will shift.'
		)

		# Keyed per budget so the confirmation does not stay ticked when the selection changes.
		if st.checkbox(f'Yes, delete {chosen}', key=f'remove_confirm_{int(row["id"])}') and st.button(
			'Delete budget', type='primary'
		):
			sql.budget.delete(int(row['id']))
			bootstrap.clear_caches()
			st.success(f'Deleted {chosen}.')
			st.rerun()
