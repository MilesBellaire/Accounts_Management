"""Shared setup for every page: import path, page chrome, cached reads, and cache
invalidation.

Import this first in each page, before anything under src/.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
	sys.path.insert(0, str(SRC_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402,F401
from database.io.dbio import sql  # noqa: E402
from logic import reports  # noqa: E402

PAGE_ICON = ':material/account_balance:'


def page(title: str, wide=True):
	"""Standard page chrome. Call once at the top of every page."""
	st.set_page_config(
		page_title=f'{title} - Accounts',
		page_icon=PAGE_ICON,
		layout='wide' if wide else 'centered',
	)
	st.title(title)


# --- Period -----------------------------------------------------------------------------
# Every page that reports over a window picks its dates here, so two pages cannot disagree
# about what "this month" means.

ALL_TIME_START = '1900-01-01'

PERIODS = [
	'All time', 'This month', 'Previous month', 'Month',
	'Last 3 months', 'Last 6 months', 'Last 12 months', 'Last 24 months', 'Custom range',
]


def _period_dates(period: str, key: str):
	today = pd.Timestamp.today().normalize()

	if period == 'All time':
		return ALL_TIME_START, reports.default_end_date()

	if period == 'This month':
		return reports.month_range(today.strftime('%Y-%m'))

	if period == 'Previous month':
		return reports.month_range((today - pd.DateOffset(months=1)).strftime('%Y-%m'))

	if period == 'Month':
		month = st.date_input('Month', value=today.replace(day=1), key=f'{key}_month')
		return reports.month_range(month.strftime('%Y-%m'))

	if period.startswith('Last '):
		# The trailing months including this one, so the window ends on today rather than on
		# the last completed month.
		count = int(period.split()[1])
		start = today.replace(day=1) - pd.DateOffset(months=count - 1)
		return start.strftime('%Y-%m-%d'), reports.default_end_date()

	chosen = st.date_input(
		'Range', value=(today.replace(month=1, day=1), today), key=f'{key}_range'
	)
	# Streamlit hands back a one-element tuple between the two clicks of a range picker.
	if len(chosen) != 2:
		st.stop()

	return (
		chosen[0].strftime('%Y-%m-%d'),
		(pd.Timestamp(chosen[1]) + pd.Timedelta(days=1)).strftime('%Y-%m-%d'),
	)


def period_picker(options=None, key='period', label='Period'):
	"""Sidebar period selector. Returns (start_date, end_date), 'YYYY-MM-DD' and end-exclusive."""
	with st.sidebar:
		st.subheader(label)
		period = st.radio(
			label, options or PERIODS, key=key, label_visibility='collapsed'
		)

		start_date, end_date = _period_dates(period, key)

		if period == 'All time':
			st.caption('All time')
		else:
			# The stored end is exclusive; the caption shows the last day actually included.
			last_day = (pd.Timestamp(end_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
			st.caption(f'{start_date} to {last_day}')

	return start_date, end_date


def clear_caches():
	"""Call after any write so the next read reflects it."""
	st.cache_data.clear()


# --- Cached reads -----------------------------------------------------------------------
# Reference data changes rarely but is read on nearly every page.

@st.cache_data(show_spinner=False)
def budgets():
	return sql.budget.get()


@st.cache_data(show_spinner=False)
def incomes():
	return sql.income.get()


@st.cache_data(show_spinner=False)
def accounts():
	return sql.get_accounts()


@st.cache_data(show_spinner=False)
def tracking_types():
	return sql.get_tracking_types()


@st.cache_data(show_spinner=False)
def budget_units():
	return sql.budget.get_units()


@st.cache_data(show_spinner=False)
def income_units():
	return sql.income.get_units()


@st.cache_data(show_spinner=False)
def constants():
	return sql.get_constants()


@st.cache_data(show_spinner=False)
def statements():
	return sql.statement.get_all()


@st.cache_data(show_spinner=False)
def keywords():
	return sql.get_keyword()


def name_to_id(df, name):
	"""Look up an id by name in a reference table, or None."""
	row = df[df['name'] == name]
	return int(row.iloc[0]['id']) if not row.empty else None


def id_to_name(df, id_value):
	row = df[df['id'] == id_value]
	return row.iloc[0]['name'] if not row.empty else None
