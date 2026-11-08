"""Month-by-month series: spending, income, and the balances they add up to.

Every series here is dense - each month in the window appears for each series, zero-filled
where nothing happened. A gap in a line reads as "no data" rather than "nothing spent", and
a running balance cannot skip a month at all, so the fill is not cosmetic.
"""

import pandas as pd

from database.io.dbio import sql
from logic import reports

MONTH = 'month'
NAME = 'name'

# The folded tail of a long series list. Not a real series, and never given a series color.
OTHER = 'other'

# Categorical palettes top out at eight slots, so seven series plus the tail is the ceiling.
SERIES_LIMIT = 7

SPENDING_COLUMNS = ['debits', 'credits', 'transfered', 'change']


def months(start_date: str, end_date: str) -> list:
	"""'YYYY-MM' for every month the window touches. End is exclusive, as everywhere else."""
	start, last = pd.Timestamp(start_date), pd.Timestamp(end_date) - pd.Timedelta(days=1)
	if last < start:
		return []
	return [str(period) for period in pd.period_range(start, last, freq='M')]


def _dense(frame: pd.DataFrame, month_list: list, value_columns: list) -> pd.DataFrame:
	"""Every series in `frame` on every month in `month_list`, missing months zero-filled."""
	if frame.empty or not month_list:
		return pd.DataFrame(columns=[MONTH, NAME] + value_columns)

	grid = pd.MultiIndex.from_product(
		[month_list, sorted(frame[NAME].unique())], names=[MONTH, NAME]
	).to_frame(index=False)

	dense = grid.merge(frame, on=[MONTH, NAME], how='left')
	dense[value_columns] = dense[value_columns].fillna(0.0)

	return dense


def monthly_spending(start_date: str, end_date: str) -> pd.DataFrame:
	"""Per-budget debits, credits, transfers and net change for each month."""
	frame = sql.budget_balance.get_monthly(start_date, end_date)
	dense = _dense(frame, months(start_date, end_date), SPENDING_COLUMNS)

	if dense.empty:
		return dense

	# The account a budget draws from belongs to the budget, not to the month, so it is
	# carried across the zero-filled rows rather than left empty on them.
	accounts = frame.drop_duplicates(NAME).set_index(NAME)['account']
	dense['account'] = dense[NAME].map(accounts).fillna('savings')

	return dense


def monthly_income(start_date: str, end_date: str) -> pd.DataFrame:
	"""Per-income credits for each month, before any distribution splits them up."""
	frame = sql.transaction.get_monthly_income(start_date, end_date)
	return _dense(frame, months(start_date, end_date), ['amount'])


def monthly_balances(start_date: str, end_date: str) -> pd.DataFrame:
	"""End-of-month balance per budget: what it opened the window with, plus each month since."""
	spending = monthly_spending(start_date, end_date)

	if spending.empty:
		return spending

	opening = (
		reports.balance_report(start_date, end_date)
		.by_budget.set_index(NAME)['initial_balance']
	)

	spending = spending.sort_values([NAME, MONTH])
	spending['balance'] = (
		spending.groupby(NAME)['change'].cumsum() + spending[NAME].map(opening).fillna(0.0)
	)

	return spending.sort_values([MONTH, NAME]).reset_index(drop=True)


def monthly_totals(start_date: str, end_date: str) -> pd.DataFrame:
	"""Money in, money out and the net, for each month across every budget."""
	spending = monthly_spending(start_date, end_date)

	if spending.empty:
		return pd.DataFrame(columns=[MONTH, 'credits', 'debits', 'net'])

	totals = spending.groupby(MONTH, as_index=False)[['credits', 'debits']].sum()
	totals['net'] = totals['credits'] - totals['debits']

	return totals


def top_series(frame: pd.DataFrame, value_column: str, limit=SERIES_LIMIT) -> pd.DataFrame:
	"""Keep the `limit` largest series and fold the rest into one 'other' row per month.

	A ninth hue is indistinguishable from one already in use, so a long tail becomes a single
	labelled series rather than a set of colors nobody can tell apart. Columns other than the
	month, the name and the value do not survive the fold.
	"""
	if frame.empty:
		return frame

	totals = frame.groupby(NAME)[value_column].sum().sort_values(ascending=False)

	if len(totals) <= limit:
		return frame[[MONTH, NAME, value_column]]

	kept = set(totals.index[:limit])
	folded = frame[[MONTH, NAME, value_column]].copy()
	folded[NAME] = folded[NAME].where(folded[NAME].isin(kept), OTHER)

	return folded.groupby([MONTH, NAME], as_index=False)[value_column].sum()


def group_series(frame: pd.DataFrame, value_column: str, mapping: dict, missing='uncategorized'):
	"""Re-key a monthly frame onto a coarser series - budgets onto their tags, say.

	Rolling up before charting is usually better than folding a tail away, because every
	budget still reaches the reader, just at a coarser grain.
	"""
	if frame.empty:
		return frame

	grouped = frame[[MONTH, NAME, value_column]].copy()
	grouped[NAME] = (
		grouped[NAME].map(mapping).replace('', pd.NA).fillna(missing)
	)

	return grouped.groupby([MONTH, NAME], as_index=False)[value_column].sum()


def as_share(frame: pd.DataFrame, value_column: str) -> pd.DataFrame:
	"""Add a `share` column: each series as a fraction of its own month's total.

	Percentages answer a different question from amounts - whether a budget is taking a
	bigger slice - and the answer changes when overall income moves.
	"""
	if frame.empty:
		return frame.assign(share=[])

	# Negatives would make a share meaningless, so the denominator is the positive part.
	positive = frame[value_column].clip(lower=0)
	totals = positive.groupby(frame[MONTH]).transform('sum')

	shared = frame.copy()
	shared['share'] = (positive / totals).where(totals > 0, 0.0)

	return shared


def latest_by(frame: pd.DataFrame, value_column: str, limit=3) -> list:
	"""The `limit` largest series in the most recent month - a default selection for a chart
	whose readable series count is far below the number of budgets."""
	if frame.empty:
		return []

	latest = frame[frame[MONTH] == frame[MONTH].max()]

	return latest.nlargest(limit, value_column)[NAME].tolist()
