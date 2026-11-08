import bootstrap
from bootstrap import sql

bootstrap.page('Constants')

import pandas as pd
import streamlit as st

import format as fmt

st.caption(
	'Named values that equations can reference as `[name]` — gas prices, mileage rates and '
	'anything else a budget is derived from.'
)

constants = bootstrap.constants()

edited = st.data_editor(
	constants,
	hide_index=True,
	width='stretch',
	num_rows='dynamic',
	key='constants_editor',
	column_config={
		'id': None,
		'name': st.column_config.TextColumn('Name', required=True, help='No spaces'),
		'value': st.column_config.NumberColumn('Value', required=True, format='%.4f'),
	},
)

st.caption('Add, edit or delete rows above, then save.')

if st.button('Save constants', type='primary'):
	before = constants.set_index('id')
	after = edited.copy()

	problems = []
	names = [str(n).strip() for n in after['name'].tolist()]
	if any(' ' in name for name in names):
		problems.append('Names cannot contain spaces')
	if len(set(names)) != len(names):
		problems.append('Names must be unique')
	if any(not name for name in names):
		problems.append('Every constant needs a name')

	if problems:
		for problem in problems:
			st.error(problem)
		st.stop()

	kept_ids = set()
	added = updated = deleted = 0

	for _, row in after.iterrows():
		row_id = row.get('id')

		if pd.isna(row_id):
			sql.insert_constant(str(row['name']).strip(), float(row['value']))
			added += 1
			continue

		row_id = int(row_id)
		kept_ids.add(row_id)

		if row_id in before.index:
			previous = before.loc[row_id]
			if previous['name'] != row['name'] or previous['value'] != row['value']:
				sql.update_constant(row_id, str(row['name']).strip(), float(row['value']))
				updated += 1

	for row_id in before.index:
		if int(row_id) not in kept_ids:
			sql.delete_constant(int(row_id))
			deleted += 1

	bootstrap.clear_caches()
	st.success(f'{added} added, {updated} updated, {deleted} deleted.')
	st.rerun()

st.divider()
st.subheader('Keywords')
st.caption(
	'Keywords auto-categorize transactions: a statement line whose description contains the '
	'keyword is assigned to that budget or income on import.'
)

keywords = bootstrap.keywords()
budgets = bootstrap.budgets()
incomes = bootstrap.incomes()

if keywords.empty:
	st.info('No keywords yet — you can add them while importing a statement.')
else:
	view = keywords.copy()
	view['budget'] = view['budget_id'].map(dict(zip(budgets['id'], budgets['name'])))
	view['income'] = view['income_id'].map(dict(zip(incomes['id'], incomes['name'])))
	view['assigns to'] = fmt.pretty_series(view['budget'].fillna(view['income'])).fillna('—')

	st.dataframe(
		view[['text', 'assigns to']].sort_values('assigns to'),
		hide_index=True,
		width='stretch',
		column_config={'text': 'Keyword', 'assigns to': 'Assigns to'},
	)

	with st.expander('Delete a keyword'):
		labels = {
			int(row['id']): f'{row["text"]}  →  {row["assigns to"]}'
			for _, row in view.iterrows()
		}
		chosen = st.selectbox('Keyword', list(labels), format_func=labels.get)
		if st.button('Delete keyword'):
			sql.delete_keyword(int(chosen))
			bootstrap.clear_caches()
			st.success('Keyword deleted.')
			st.rerun()
