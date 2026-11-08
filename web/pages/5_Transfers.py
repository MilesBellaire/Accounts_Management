import bootstrap

bootstrap.page('Transfers')

import streamlit as st

import format as fmt
from logic import transfers as transfer_logic


@st.cache_data(show_spinner=False)
def balances():
	return transfer_logic.budget_balances()


@st.cache_data(show_spinner=False)
def history():
	return transfer_logic.transfer_history()


current = balances()

st.caption(
	'A transfer moves money between budget balances without inventing a transaction — use it '
	'when one bucket has piled up and another has run short.'
)

if current.empty:
	st.info('No budget balances to transfer between yet.')
	st.stop()

options = current.sort_values('name')
labels = {
	int(row['budget_id']): f'{fmt.pretty(row["name"])}  ({fmt.money(row["balance"])})'
	for _, row in options.iterrows()
}

left, right = st.columns(2)

with left:
	from_id = st.selectbox(
		'From', list(labels), format_func=labels.get, key='from_budget'
	)
with right:
	to_id = st.selectbox(
		'To', list(labels), format_func=labels.get, index=min(1, len(labels) - 1), key='to_budget'
	)

amount = st.number_input('Amount', min_value=0.0, step=25.0, value=0.0, format='%.2f')

error = transfer_logic.validate_transfer(from_id, to_id, amount, balances=current)

if amount > 0:
	source_before, source_after, dest_before, dest_after = transfer_logic.preview_transfer(
		from_id, to_id, amount, balances=current
	)

	preview_left, preview_right = st.columns(2)
	with preview_left:
		st.metric(
			fmt.pretty(bootstrap.id_to_name(current.rename(columns={'budget_id': 'id'}), from_id)) or 'From',
			fmt.money(source_after),
			delta=fmt.money(-amount),
		)
	with preview_right:
		st.metric(
			fmt.pretty(bootstrap.id_to_name(current.rename(columns={'budget_id': 'id'}), to_id)) or 'To',
			fmt.money(dest_after),
			delta=fmt.money(amount),
		)

if error:
	st.warning(error)

if st.button('Make transfer', type='primary', disabled=bool(error)):
	transfer_logic.apply_transfer(from_id, to_id, amount)
	bootstrap.clear_caches()
	st.success(f'Transferred {fmt.money(amount)}.')
	st.rerun()

st.divider()
st.subheader('Past transfers')

past = history()

if past.empty:
	st.info('No transfers yet.')
else:
	shown = past.copy()
	shown['from_budget'] = fmt.pretty_series(shown['from_budget'])
	shown['to_budget'] = fmt.pretty_series(shown['to_budget'])
	st.dataframe(
		shown,
		hide_index=True,
		width='stretch',
		column_config={
			'id': st.column_config.NumberColumn('ID', format='%d', width='small'),
			'date': st.column_config.DatetimeColumn('Date', format='YYYY-MM-DD'),
			'amount': fmt.money_column('Amount'),
			'from_budget': 'From',
			'to_budget': 'To',
		},
	)

	with st.expander('Undo a transfer'):
		st.caption('Deleting a transfer moves the money straight back.')
		chosen = st.selectbox(
			'Transfer',
			past['id'].tolist(),
			format_func=lambda i: (
				lambda r: f'{r["date"][:10]}  {fmt.pretty(r["from_budget"])} → {fmt.pretty(r["to_budget"])}  {fmt.money(r["amount"])}'
			)(past[past['id'] == i].iloc[0]),
		)
		if st.button('Delete transfer'):
			transfer_logic.sql.budget_balance.delete_transfer(int(chosen))
			bootstrap.clear_caches()
			st.success('Transfer deleted.')
			st.rerun()
