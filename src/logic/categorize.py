"""Assigning a budget (debits) or an income (credits) to parsed transactions.

Each description is matched against the keyword table. A single match is applied outright;
zero or several matches are left blank for a person to resolve.
"""

import pandas as pd

from database.io.dbio import sql

UNKNOWN_ID = -1


def keyword_matches(description: str, debit_or_credit: str) -> pd.DataFrame:
	"""Budgets (for a debit) or incomes (for a credit) whose keywords match this description."""
	if debit_or_credit == '-':
		return sql.budget.get_id_by_keyword(description)
	return sql.income.get_id_by_keyword(description)


def suggest_categories(transactions: pd.DataFrame) -> pd.DataFrame:
	"""Fill Category/AssociatedId wherever exactly one keyword matches.

	Transfers between the user's own accounts are skipped: they are neither income nor
	spending. Ambiguous and unmatched rows come back blank.
	"""
	transactions = transactions.copy()

	for i, row in transactions.iterrows():
		if row['IsTransfer'] == 1:
			continue

		matches = keyword_matches(row['Description'], row['DebitOrCredit'])
		if len(matches) == 1:
			transactions.loc[i, 'Category'] = matches['name'].iloc[0]
			transactions.loc[i, 'AssociatedId'] = matches['id'].iloc[0]

	return transactions


def category_options(debit_or_credit: str) -> pd.DataFrame:
	"""The budgets or incomes a transaction of this kind can be assigned to, plus Unknown."""
	options = (sql.budget.get() if debit_or_credit == '-' else sql.income.get())[['id', 'name']]
	return pd.concat(
		[options, pd.DataFrame({'name': ['Unknown'], 'id': [UNKNOWN_ID]})], ignore_index=True
	)


def tracks_by_keyword(category_id: int, debit_or_credit: str) -> bool:
	"""Whether this budget/income learns from keywords, i.e. whether offering to save a new
	keyword for it makes sense."""
	if category_id is None or int(category_id) == UNKNOWN_ID:
		return False

	table = sql.budget.get() if debit_or_credit == '-' else sql.income.get()
	row = table[table['id'] == int(category_id)]

	return not row.empty and row['tracking_type'].iloc[0] == 'keyword'


def unresolved(transactions: pd.DataFrame) -> pd.DataFrame:
	"""Rows that still need a category before they can be staged."""
	needs_category = transactions['AssociatedId'].isin(['', None]) | transactions[
		'AssociatedId'
	].isna()
	return transactions[needs_category & (transactions['IsTransfer'] != 1)]
