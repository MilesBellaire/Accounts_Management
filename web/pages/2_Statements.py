import bootstrap
from bootstrap import sql

bootstrap.page('Statements')

import pandas as pd
import streamlit as st

import config
import format as fmt
from logic import categorize, parsers
from logic.distribution_weights import update_budget_distribution_weights

UNASSIGNED = '—'

budgets = bootstrap.budgets()
incomes = bootstrap.incomes()

upload_tab, manage_tab = st.tabs(['Import a statement', 'Imported statements'])


def category_names(debit_or_credit):
	table = budgets if debit_or_credit == '-' else incomes
	return [UNASSIGNED] + fmt.pretty_list(table['name']) + ['Unknown']


def resolve_category_id(name, debit_or_credit):
	"""Label chosen in the editor -> the id to store, or None if still unassigned."""
	if name in (UNASSIGNED, None, ''):
		return None
	if name == 'Unknown':
		return categorize.UNKNOWN_ID
	table = budgets if debit_or_credit == '-' else incomes
	# The editor shows pretty labels, so map back to the stored name before looking up the id.
	stored = fmt.unpretty_map(table['name']).get(name, name)
	return bootstrap.name_to_id(table, stored)


# --- Import ------------------------------------------------------------------------------

with upload_tab:
	uploaded = st.file_uploader('Statement PDF', type='pdf')

	local = sorted(p.stem for p in config.STATEMENTS_DIR.glob('*.pdf'))
	chosen_local = st.selectbox(
		'…or one already in data/Statements',
		['—'] + local,
		help=str(config.STATEMENTS_DIR),
	)

	name = None
	if uploaded is not None:
		name = pd.Series([uploaded.name]).str.replace(r'\.pdf$', '', regex=True).iloc[0]
		target = config.STATEMENTS_DIR / f'{name}.pdf'
		config.STATEMENTS_DIR.mkdir(parents=True, exist_ok=True)
		target.write_bytes(uploaded.getbuffer())
		st.caption(f'Saved to {target}')
	elif chosen_local != '—':
		name = chosen_local

	if name is None:
		st.info('Upload a statement PDF, or pick one already on disk, to begin.')
		st.stop()

	try:
		parsed = parsers.parse_statement_file(name)
	except parsers.ParseError as exc:
		st.error(str(exc))
		st.stop()
	except Exception as exc:
		st.error(f'Could not read this statement: {exc}')
		st.stop()

	a, b, c = st.columns(3)
	a.metric('Type', parsed.kind)
	b.metric('Period', f'{parsed.start_date:%Y-%m-%d} → {parsed.end_date:%Y-%m-%d}')
	c.metric('Transactions found', len(parsed.transactions))

	# Overwrite guard: re-importing must remove the old rows first or they double up.
	overwrite = False
	if sql.statement.exists(parsed.name):
		existing_id = sql.statement.get_id(parsed.name)
		st.warning(
			f'**{parsed.name}** has already been imported. Re-importing deletes the existing '
			'transactions and their distributions, then re-adds them.'
		)
		overwrite = st.checkbox(f'Replace the existing import of {parsed.name}')
		if not overwrite:
			st.stop()

	suggested = categorize.suggest_categories(parsed.transactions)
	suggested['Category'] = fmt.pretty_series(suggested['Category']).replace('', UNASSIGNED)

	transfers = suggested[suggested['IsTransfer'] == 1]
	debits = suggested[(suggested['IsTransfer'] != 1) & (suggested['DebitOrCredit'] == '-')]
	credits = suggested[(suggested['IsTransfer'] != 1) & (suggested['DebitOrCredit'] == '+')]

	st.divider()
	st.subheader('Categorize')
	st.caption(
		'Rows a keyword matched are filled in already. Set a category on the rest — '
		'transfers between your own accounts need none.'
	)

	def editor(df, debit_or_credit, key):
		if df.empty:
			return df
		view = df[['Date', 'Description', 'Amount', 'Account', 'Category']].copy()
		return st.data_editor(
			view,
			hide_index=True,
			width='stretch',
			key=key,
			disabled=['Date', 'Description', 'Amount', 'Account'],
			column_config={
				'Date': st.column_config.DateColumn('Date', format='YYYY-MM-DD', width='small'),
				'Description': st.column_config.TextColumn('Description', width='large'),
				'Amount': fmt.money_column('Amount'),
				'Account': st.column_config.TextColumn('Account', width='small'),
				'Category': st.column_config.SelectboxColumn(
					'Budget' if debit_or_credit == '-' else 'Income',
					options=category_names(debit_or_credit),
					required=False,
				),
			},
		)

	st.markdown(f'**Spending** ({len(debits)})')
	edited_debits = editor(debits, '-', 'debit_editor')

	st.markdown(f'**Income** ({len(credits)})')
	edited_credits = editor(credits, '+', 'credit_editor')

	if not transfers.empty:
		with st.expander(f'Transfers between your accounts ({len(transfers)}) — no category needed'):
			st.dataframe(
				transfers[['Date', 'Description', 'Amount', 'Account', 'DebitOrCredit']],
				hide_index=True,
				width='stretch',
				column_config={'Amount': fmt.money_column('Amount')},
			)

	# Fold the editors back onto the parsed frame.
	staged = suggested.copy()
	for edited, debit_or_credit in ((edited_debits, '-'), (edited_credits, '+')):
		if edited is None or len(edited) == 0:
			continue
		for index, row in edited.iterrows():
			staged.loc[index, 'Category'] = row['Category']
			staged.loc[index, 'AssociatedId'] = resolve_category_id(row['Category'], debit_or_credit)

	staged.loc[staged['IsTransfer'] == 1, 'Category'] = ''
	staged.loc[staged['IsTransfer'] == 1, 'AssociatedId'] = None
	staged['Category'] = staged['Category'].replace(UNASSIGNED, '')

	missing = staged[(staged['IsTransfer'] != 1) & (staged['AssociatedId'].isna())]

	st.divider()

	# Offer to teach a keyword for anything newly categorized under a keyword-tracked budget.
	newly_set = staged[
		(staged['IsTransfer'] != 1)
		& staged['AssociatedId'].notna()
		& (suggested['Category'].isin([UNASSIGNED, '']))
	]
	keyword_candidates = [
		row for _, row in newly_set.iterrows()
		if categorize.tracks_by_keyword(row['AssociatedId'], row['DebitOrCredit'])
	]

	new_keywords = {}
	if keyword_candidates:
		with st.expander(f'Teach keywords ({len(keyword_candidates)} categorized by hand)'):
			st.caption(
				'A keyword saved here auto-categorizes future transactions whose description '
				'contains it.'
			)
			for row in keyword_candidates:
				new_keywords[row.name] = st.text_input(
					f'{row["Description"]}  →  {row["Category"]}',
					key=f'keyword_{row.name}',
					placeholder='leave empty to skip',
				)

	if not missing.empty:
		st.error(f'{len(missing)} transaction(s) still need a category before this can be imported.')
		st.dataframe(
			missing[['Date', 'Description', 'Amount', 'DebitOrCredit']],
			hide_index=True,
			width='stretch',
		)
	elif st.button('Import statement', type='primary'):
		# Budget weights must add to 100% per income or the balances come out wrong.
		weights = update_budget_distribution_weights()
		if not weights.ok:
			st.error(weights.message)
			st.dataframe(weights.sums, width='stretch')
			st.caption('Fix the budget or income values on the Plan page, then import again.')
			st.stop()

		if overwrite:
			sql.statement.delete(sql.statement.get_id(parsed.name))

		statement_id = sql.statement.insert(parsed.name, parsed.start_date, parsed.end_date)
		staged['StatementId'] = statement_id

		sql.statement.stage_transactions(staged)

		for index, keyword in new_keywords.items():
			if not keyword.strip():
				continue
			row = staged.loc[index]
			if row['DebitOrCredit'] == '-':
				sql.insert_keyword(keyword.strip(), budget_id=int(row['AssociatedId']))
			else:
				sql.insert_keyword(keyword.strip(), income_id=int(row['AssociatedId']))

		bootstrap.clear_caches()
		st.success(f'Imported {len(staged)} transactions from {parsed.name}.')
		st.balloons()

# --- Manage ------------------------------------------------------------------------------

with manage_tab:
	imported = bootstrap.statements()

	if imported.empty:
		st.info('Nothing imported yet.')
	else:
		st.dataframe(
			imported,
			hide_index=True,
			width='stretch',
			column_config={
				'id': st.column_config.NumberColumn('ID', format='%d', width='small'),
				'name': 'Statement',
				'start_date': st.column_config.DatetimeColumn('From', format='YYYY-MM-DD'),
				'end_date': st.column_config.DatetimeColumn('To', format='YYYY-MM-DD'),
				'transactions': st.column_config.NumberColumn('Transactions', format='%d'),
				'debits': fmt.money_column('Out'),
				'credits': fmt.money_column('In'),
			},
		)

		st.divider()
		st.subheader('Delete an import')
		st.caption(
			'Removes the statement, its transactions, and any distributions used only by it. '
			'The PDF on disk is left alone.'
		)

		to_delete = st.selectbox('Statement', ['—'] + imported['name'].tolist())
		if to_delete != '—':
			row = imported[imported['name'] == to_delete].iloc[0]
			st.warning(f'This deletes {int(row["transactions"])} transaction(s).')
			if st.checkbox(f'Yes, delete {to_delete}') and st.button('Delete', type='primary'):
				sql.statement.delete(int(row['id']))
				bootstrap.clear_caches()
				st.success(f'Deleted {to_delete}.')
				st.rerun()
