"""The ideal-budget views: where money should go, as opposed to where it went.

Both tables are built from shared_logic.generate_accounts_df; this module only reshapes it
for display and reports the sanity checks.
"""

from dataclasses import dataclass, field

import pandas as pd

from database.io.dbio import sql
from logic import shared_logic

# Income rows are tagged with this in both tables' group column.
INCOME_GROUP = 'income'

PERIODS = {
	'Per Day': 1 / 30.437,
	'Per Week': 1 / 4.345,
	'Per Month': 1,
	'Per Year': 12,
	'Per 5 Years': 60,
}


@dataclass
class Section:
	name: str
	rows: pd.DataFrame
	subtotals: pd.Series


@dataclass
class PlanTable:
	table: pd.DataFrame
	group_column: str
	warnings: list = field(default_factory=list)

	@property
	def value_columns(self):
		return [
			c for c in self.table.columns
			if c != self.group_column and pd.api.types.is_numeric_dtype(self.table[c])
		]

	def sections(self, sort_by='Per Month'):
		"""One Section per group, largest first, each with its own subtotals.

		The CLI printed the same shape - a block per category with a total row - which is
		much easier to read than one long undivided table.
		"""
		groups = []
		for name in self.table[self.group_column].unique():
			rows = self.table[self.table[self.group_column] == name]
			if rows.empty:
				continue
			groups.append(Section(str(name), rows, rows[self.value_columns].sum()))

		key = sort_by if sort_by in self.value_columns else self.value_columns[0]
		return sorted(groups, key=lambda s: s.subtotals.get(key, 0), reverse=True)

	@property
	def totals(self):
		return self.table[self.value_columns].sum()

	@property
	def expenses(self):
		"""Everything except the income rows."""
		return self.table[self.table[self.group_column] != INCOME_GROUP]

	@property
	def income(self):
		return self.table[self.table[self.group_column] == INCOME_GROUP]

	@property
	def expense_totals(self):
		"""Totals across the budgets only.

		Income funds all of it, so adding income into the same total would double-count.
		"""
		return self.expenses[self.value_columns].sum()

	@property
	def income_totals(self):
		return self.income[self.value_columns].sum()


def _sanity_warnings(df: pd.DataFrame, group_column: str) -> list:
	"""The three checks both CLI views used to print after the table."""
	warnings = []

	is_income = df[group_column] == 'income'
	income_percentage = round(df[is_income]['Percentage'].sum())
	expense_percentage = round(df[~is_income]['Percentage'].sum())
	income_total = round(df[is_income]['Per Month'].sum())
	expense_total = round(df[~is_income]['Per Month'].sum())

	if income_percentage != 1:
		warnings.append(f'Income percentages do not add up to 100% (sum: {income_percentage:.0%})')
	if expense_percentage != 1:
		warnings.append(f'Expense percentages do not add up to 100% (sum: {expense_percentage:.0%})')
	if income_total != expense_total:
		warnings.append(
			f'Income and expenses do not balance (income ${income_total:,}, expenses ${expense_total:,})'
		)

	return warnings


def timeline_table(takehome: bool) -> PlanTable:
	"""Every income and budget, expressed across each time period."""
	df, lp_warnings = shared_logic.generate_accounts_df(not takehome)

	table = df[['Name', 'Category', 'Percentage']].copy()
	# 'Per Month' is itself one of the periods, so it is rebuilt here rather than carried over.
	for label, multiplier in PERIODS.items():
		table[label] = df['Per Month'] * multiplier

	return PlanTable(
		table=table,
		group_column='Category',
		warnings=lp_warnings + _sanity_warnings(df, 'Category'),
	)


def percentage_table(takehome: bool) -> PlanTable:
	"""Every budget with the share each income contributes to it."""
	df, lp_warnings = shared_logic.generate_accounts_df(not takehome)
	df = df.drop(columns=['id'])

	budgets = sql.budget.get()
	account_by_name = dict(zip(budgets['name'], budgets['account']))

	df['Account'] = df['Name'].map(account_by_name).fillna('income')
	df.loc[df['Name'] == 'Leftover', 'Account'] = 'savings'

	# Order accounts by how much of the budget they represent.
	order = df.groupby('Account')['Percentage'].sum().sort_values(ascending=False).index.tolist()
	df['Account'] = pd.Categorical(df['Account'], categories=order, ordered=True)
	df = df.sort_values(['Account', 'Percentage'], ascending=[True, False])

	allocation_columns = [c for c in df.columns if c.endswith(' %') or c.endswith(' $')]
	table = df[['Name', 'Account', 'Percentage', 'Per Month'] + allocation_columns]

	return PlanTable(
		table=table,
		group_column='Account',
		warnings=lp_warnings + _sanity_warnings(df, 'Account'),
	)
