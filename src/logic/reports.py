"""Balance reporting over the budget_transact / budget_balance views."""

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from database.io.dbio import sql

BALANCE_COLUMNS = ['initial_balance', 'debits', 'credits', 'transfered', 'change', 'balance']


def default_end_date() -> str:
	"""Tomorrow, so that everything recorded today is included."""
	return (pd.to_datetime('now') + timedelta(days=1)).strftime('%Y-%m-%d')


@dataclass
class BalanceReport:
	start_date: str
	end_date: str
	by_budget: pd.DataFrame
	by_account: pd.DataFrame
	totals: pd.Series

	@property
	def empty(self) -> bool:
		return self.by_budget.empty


def balance_report(start_date='1900-01-01', end_date=None) -> BalanceReport:
	end_date = end_date or default_end_date()

	report = sql.budget_balance.get_asof(start_date, end_date)
	report = report[[col for col in report.columns if '_id' not in col]]

	if report.empty:
		return BalanceReport(start_date, end_date, report, report, pd.Series(dtype=float))

	# Budgets with no account are savings buckets.
	report['account'] = report['account'].fillna('savings')

	by_budget = report.sort_values(['account', 'name']).round(2).reset_index(drop=True)
	by_account = report.groupby('account')[BALANCE_COLUMNS].sum().round(2).reset_index()
	totals = report[BALANCE_COLUMNS].sum().round(2)

	return BalanceReport(start_date, end_date, by_budget, by_account, totals)


def month_range(month: str):
	"""('2025-07') -> ('2025-07-01', '2025-08-01')"""
	start = pd.to_datetime(month).to_period('M')
	return str(start) + '-01', str(start + 1) + '-01'


def account_diff():
	"""System-tracked budget balances against the actual account balances.

	A non-zero diff means transactions are missing or miscategorised.
	"""
	df = sql.get_account_balance_diffs().round(2)
	totals = df[['budget_balance', 'account_balance', 'diff']].sum().round(2)
	return df, totals
