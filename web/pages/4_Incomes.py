import bootstrap
from bootstrap import sql

bootstrap.page('Incomes')

import streamlit as st

import format as fmt
from logic import equations

incomes = bootstrap.incomes()
units = bootstrap.income_units()
tracking_types = bootstrap.tracking_types()
budgets = bootstrap.budgets()

view_tab, add_tab, edit_tab, remove_tab = st.tabs(['View', 'Add', 'Edit', 'Remove'])


def unit_options():
	return units['abv'].tolist()


def attached_budgets(row):
	return [b for b in (row['budgets'] or '').split(', ') if b]


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


# --- View --------------------------------------------------------------------------------

with view_tab:
	if incomes.empty:
		st.info('No incomes yet.')
	else:
		shown = incomes[['name', 'unit', 'value', 'equation', 'tags', 'tracking_type', 'budgets', 'id']].copy()
		shown['name'] = fmt.pretty_series(shown['name'])
		shown['budgets'] = shown['budgets'].map(
			lambda b: ', '.join(fmt.pretty_list([x for x in (b or '').split(', ') if x]))
		)
		st.dataframe(
			shown,
			hide_index=True,
			width='stretch',
			column_config={
				'name': 'Name',
				'unit': st.column_config.TextColumn('Unit', width='small'),
				'value': st.column_config.NumberColumn('Value', format='%.2f'),
				'equation': st.column_config.TextColumn('Equation', width='medium'),
				'tags': 'Tags',
				'tracking_type': 'Tracking',
				'budgets': st.column_config.TextColumn('Funds these budgets', width='large'),
				'id': st.column_config.NumberColumn('ID', format='%d', width='small'),
			},
		)
		st.caption(
			'The budgets column is the income\'s primary distribution — which budgets its money '
			'is split across. The split itself is solved on the Plan page.'
		)

# --- Add ---------------------------------------------------------------------------------

with add_tab:
	name = st.text_input('Name', key='add_name', help='Lowercase, no spaces')
	unit = st.selectbox('Unit', unit_options(), key='add_unit')
	value = st.number_input(
		'Value ($ per month)' if unit in ('$', 'eq') else 'Value (%)', value=0.0, key='add_value'
	)

	equation, equation_ok = ('', True)
	if unit == 'eq':
		equation, equation_ok = equation_input('Equation', key='add_equation')

	tracking_type = st.selectbox('Tracking type', tracking_types['name'].tolist(), key='add_tracking')
	tags = st.text_input('Tags', key='add_tags')
	attached = st.multiselect(
		'Funds these budgets', budgets['name'].tolist(), format_func=fmt.pretty, key='add_budgets'
	)

	problems = []
	if not name.strip():
		problems.append('Name is required')
	elif ' ' in name.strip():
		problems.append('Name cannot contain spaces')
	elif name.strip().lower() in incomes['name'].tolist():
		problems.append('An income with that name already exists')
	if unit == 'eq' and not equation_ok:
		problems.append('Fix the equation')

	for problem in problems:
		st.warning(problem)

	if st.button('Add income', type='primary', disabled=bool(problems)):
		sql.income.insert(
			name.strip().lower(),
			equation or None,
			tags,
			bootstrap.name_to_id(tracking_types, tracking_type),
			int(units[units['abv'] == unit].iloc[0]['id']),
			value,
			[bootstrap.name_to_id(budgets, b) for b in attached],
		)
		bootstrap.clear_caches()
		st.success(f'Added {name.strip().lower()}.')
		st.rerun()

# --- Edit --------------------------------------------------------------------------------

with edit_tab:
	editable = incomes[incomes['name'] != 'other']

	if editable.empty:
		st.info('No incomes to edit.')
	else:
		chosen = st.selectbox(
			'Income', editable['name'].tolist(), format_func=fmt.pretty, key='edit_choice'
		)
		row = editable[editable['name'] == chosen].iloc[0]

		# Streamlit ignores value=/index=/default= once a key already holds state, so the keys
		# carry the income id: picking a different income makes fresh widgets showing its values.
		k = f'_{int(row["id"])}'

		new_name = st.text_input(
			'Name', value=row['name'], key=f'edit_name{k}',
			help='Stored lowercase with underscores; tables and charts show it prettified',
		)
		new_unit = st.selectbox(
			'Unit', unit_options(), index=unit_options().index(row['unit']), key=f'edit_unit{k}'
		)
		new_value = st.number_input(
			'Value ($ per month)' if new_unit in ('$', 'eq') else 'Value (%)',
			value=float(row['value'] or 0.0),
			key=f'edit_value{k}',
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
		new_tags = st.text_input('Tags', value=row['tags'] or '', key=f'edit_tags{k}')
		new_budgets = st.multiselect(
			'Funds these budgets',
			budgets['name'].tolist(),
			format_func=fmt.pretty,
			default=[b for b in attached_budgets(row) if b in budgets['name'].tolist()],
			key=f'edit_budgets{k}',
		)

		st.caption(
			'Changing which budgets an income funds rebuilds its distribution, so the weights '
			'are recalculated the next time a statement is imported.'
		)

		if st.button('Save income', type='primary', disabled=not equation_ok):
			sql.income.update(
				int(row['id']),
				new_name.strip().lower(),
				new_equation or None,
				new_tags,
				bootstrap.name_to_id(tracking_types, new_tracking),
				int(units[units['abv'] == new_unit].iloc[0]['id']),
				new_value,
				[bootstrap.name_to_id(budgets, b) for b in new_budgets],
			)
			bootstrap.clear_caches()
			st.success(f'Saved {new_name}.')
			st.rerun()

# --- Remove ------------------------------------------------------------------------------

with remove_tab:
	removable = incomes[incomes['name'] != 'other']

	if removable.empty:
		st.info('No incomes to remove.')
	else:
		chosen = st.selectbox(
			'Income', removable['name'].tolist(), format_func=fmt.pretty, key='remove_choice'
		)
		row = removable[removable['name'] == chosen].iloc[0]

		st.warning(
			f'Deleting **{chosen}** unassigns its transactions (they become category -1) and '
			'removes its distributions. Balances will shift.'
		)

		# Keyed per income so the confirmation does not stay ticked when the selection changes.
		if st.checkbox(f'Yes, delete {chosen}', key=f'remove_confirm_{int(row["id"])}') and st.button(
			'Delete income', type='primary'
		):
			sql.income.delete(int(row['id']))
			bootstrap.clear_caches()
			st.success(f'Deleted {chosen}.')
			st.rerun()
