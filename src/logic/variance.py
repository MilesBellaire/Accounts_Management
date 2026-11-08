"""Planned spending against actual spending.

`plan.timeline_table` says what each budget should get per month; `reports.balance_report`
says what each one actually spent over a window. This joins the two, so a budget can be read
as under, near, or over its plan rather than as a bare balance.

Targets are pro-rated: a window is measured in months, and a budget's target is its
per-month plan times that. A window that has not finished yet also carries an `expected`
figure - the plan up to today - and a `projected` one, which is the current rate of spend
carried out to the end of the window.
"""

from dataclasses import dataclass, field

import pandas as pd

from logic import plan, reports, shared_logic

# The same figure plan.PERIODS uses to turn a per-month amount into a per-day one.
DAYS_PER_MONTH = 30.437

# Share of the target spent, at which a budget stops being comfortable.
NEAR_LIMIT = 0.9

# The residual row the plan appends; it is not a bucket anything can be spent from, so it
# has no actual to compare against.
RESIDUAL = 'Leftover'

UNPLANNED = 'unplanned'
UNCATEGORIZED = 'uncategorized'

# Worst first: a report is read to find the problems, not to admire the budgets that held.
STATUS_ORDER = ['over', UNPLANNED, 'near', 'under']

ROW_COLUMNS = [
	'name', 'category', 'account', 'target', 'actual', 'variance',
	'used', 'expected', 'projected', 'status',
]

MONEY_COLUMNS = ['target', 'actual', 'variance', 'expected', 'projected']


@dataclass
class VarianceReport:
	start_date: str
	end_date: str
	months: float
	elapsed_months: float
	rows: pd.DataFrame
	warnings: list = field(default_factory=list)

	@property
	def empty(self) -> bool:
		return self.rows.empty

	@property
	def in_progress(self) -> bool:
		"""Whether the window runs past today, so the targets are not all due yet."""
		return self.elapsed_months < self.months - 0.01

	@property
	def elapsed_share(self) -> float:
		return self.elapsed_months / self.months if self.months else 0.0

	@property
	def totals(self) -> pd.Series:
		if self.empty:
			return pd.Series(0.0, index=MONEY_COLUMNS + ['used'])

		totals = self.rows[MONEY_COLUMNS].sum()
		totals['used'] = totals['actual'] / totals['target'] if totals['target'] else float('nan')
		return totals

	def with_status(self, *statuses) -> pd.DataFrame:
		return self.rows[self.rows['status'].isin(statuses)]

	@property
	def needs_attention(self) -> pd.DataFrame:
		"""Over its target, or spent with no plan at all."""
		return self.with_status('over', UNPLANNED)


def months_between(start_date, end_date) -> float:
	"""Length of a window in months. End is exclusive, as everywhere else."""
	days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days
	return max(days, 0) / DAYS_PER_MONTH


def _targets(takehome: bool):
	"""Per-budget monthly plan, and whatever the plan itself is unhappy about."""
	table = plan.timeline_table(takehome)

	targets = table.expenses.rename(
		columns={'Name': 'name', 'Category': 'category', 'Per Month': 'per_month'}
	)[['name', 'category', 'per_month']]

	targets = targets[targets['name'] != RESIDUAL].copy()
	targets['category'] = targets['category'].fillna(UNCATEGORIZED).replace('', UNCATEGORIZED)

	return targets, table.warnings


def _actuals(start_date: str, end_date: str) -> pd.DataFrame:
	"""Per-budget spending over the window. Debits only: transfers are not spending."""
	report = reports.balance_report(start_date, end_date)

	if report.empty:
		return pd.DataFrame(columns=['name', 'account', 'actual'])

	return report.by_budget[['name', 'account', 'debits']].rename(columns={'debits': 'actual'})


def _status(target: float, actual: float, used: float) -> str:
	if target <= 0:
		return UNPLANNED if actual > 0 else 'under'
	if actual > target:
		return 'over'
	return 'near' if used >= NEAR_LIMIT else 'under'


def build_rows(targets, actuals, months, elapsed_months, takehome=False):
	"""Join a per-month plan to actual spending over a window of `months`.

	Pure: both frames come from the caller. `targets` carries name/category/per_month,
	`actuals` carries name/account/actual. Budgets on one side only are kept - spending with
	no plan behind it is the single most useful thing this table has to say.
	"""
	rows = targets.merge(actuals, on='name', how='outer')

	if takehome:
		# The plan has folded these out of salary, so their actuals would otherwise come back
		# as a large lump of unplanned spending.
		rows = rows[~rows['name'].isin(shared_logic.EXTERNAL_BUDGETS)].copy()

	rows['per_month'] = rows['per_month'].fillna(0.0)
	rows['actual'] = rows['actual'].fillna(0.0)
	rows['category'] = rows['category'].fillna(UNPLANNED)
	# balance_report calls a budget with no account a savings bucket; stay consistent with it.
	rows['account'] = rows['account'].fillna('savings')

	rows['target'] = rows['per_month'] * months
	rows['expected'] = rows['per_month'] * elapsed_months
	rows['variance'] = rows['target'] - rows['actual']
	rows['used'] = (rows['actual'] / rows['target']).where(rows['target'] > 0)
	# What the rate of spend so far comes to by the end of the window.
	rows['projected'] = (
		rows['actual'] / elapsed_months * months if elapsed_months else rows['actual']
	)

	rows['status'] = [
		_status(row['target'], row['actual'], row['used']) for _, row in rows.iterrows()
	]

	# A budget with no plan and no spending in this window is noise, not a finding.
	rows = rows[(rows['target'] > 0) | (rows['actual'] > 0)]

	# Most overspent first, so the table opens on whatever needs doing something about.
	rows = rows.sort_values(['variance', 'actual'], ascending=[True, False])

	return rows[ROW_COLUMNS].round(2).reset_index(drop=True)


def variance_report(start_date: str, end_date: str, takehome=False, today=None) -> VarianceReport:
	"""Every budget's planned spending against what it actually spent over [start, end)."""
	months = months_between(start_date, end_date)

	today = pd.Timestamp.today().normalize() if today is None else pd.Timestamp(today).normalize()
	# Today counts as elapsed, matching reports.default_end_date's exclusive end of tomorrow.
	elapsed_end = min(pd.Timestamp(end_date), today + pd.Timedelta(days=1))
	elapsed_months = min(months_between(start_date, elapsed_end), months)

	targets, warnings = _targets(takehome)
	actuals = _actuals(start_date, end_date)

	return VarianceReport(
		start_date=start_date,
		end_date=end_date,
		months=months,
		elapsed_months=elapsed_months,
		rows=build_rows(targets, actuals, months, elapsed_months, takehome),
		warnings=warnings,
	)


def by_category(report: VarianceReport) -> pd.DataFrame:
	"""The same comparison rolled up to the plan's categories."""
	if report.empty:
		return pd.DataFrame(columns=['category'] + MONEY_COLUMNS + ['used'])

	grouped = report.rows.groupby('category', as_index=False)[MONEY_COLUMNS].sum()
	grouped['used'] = (grouped['actual'] / grouped['target']).where(grouped['target'] > 0)
	grouped['status'] = [
		_status(row['target'], row['actual'], row['used']) for _, row in grouped.iterrows()
	]

	return grouped.sort_values('variance').round(2).reset_index(drop=True)
