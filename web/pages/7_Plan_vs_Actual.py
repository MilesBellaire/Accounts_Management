import bootstrap

bootstrap.page('Plan vs Actual')

import streamlit as st

import format as fmt
from logic import variance

st.caption(
	'What each budget was meant to spend over this period, against what it actually spent. '
	'The Plan page sets the targets; the Dashboard shows the balances they produce.'
)


@st.cache_data(show_spinner=False)
def report(start_date, end_date, takehome):
	return variance.variance_report(start_date, end_date, takehome)


@st.cache_data(show_spinner=False)
def categories(start_date, end_date, takehome):
	return variance.by_category(variance.variance_report(start_date, end_date, takehome))


COLUMNS = {
	'name': st.column_config.TextColumn('Budget', width='medium'),
	'category': st.column_config.TextColumn('Category', width='small'),
	'target': fmt.money_column('Target'),
	'actual': fmt.money_column('Spent'),
	'variance': fmt.money_column('Left', help='Negative means over target'),
	'used': st.column_config.ProgressColumn(
		'Used', format='percent', min_value=0, max_value=1,
	),
	'expected': fmt.money_column('Expected by now'),
	'projected': fmt.money_column('On track for', help='The rate so far, carried to the end'),
	'status': st.column_config.TextColumn('Status', width='small'),
}


def for_display(df):
	"""Stored names are lowercase with underscores; tables show the pretty form."""
	shown = df.copy()
	for column in ('name', 'category'):
		if column in shown:
			shown[column] = fmt.pretty_series(shown[column])
	shown['status'] = shown['status'].map(fmt.VARIANCE_LABELS)
	return shown


# --- Period ------------------------------------------------------------------------------

start_date, end_date = bootstrap.period_picker([
	'This month', 'Previous month', 'Month',
	'Last 3 months', 'Last 6 months', 'Last 12 months', 'Custom range',
])

with st.sidebar:
	takehome = st.toggle(
		'Take-home only',
		key='takehome',
		help='Fold taxes and 401k out of salary instead of comparing them as budgets',
	)

result = report(start_date, end_date, takehome)

if result.empty:
	st.info('Nothing to compare in this period — no targets and no spending.')
	st.stop()

# The plan not adding up makes every target on this page suspect, so it is said first.
for warning in result.warnings:
	st.warning(warning)

# --- Headline numbers --------------------------------------------------------------------

totals = result.totals
target, spent, left, used = st.columns(4)

with target:
	fmt.stat('Target', fmt.money(totals['target']), help=f'{result.months:.1f} months of plan')
with spent:
	fmt.stat('Spent', fmt.money(totals['actual']))
with left:
	fmt.stat(
		'Left to spend',
		fmt.money(totals['variance']),
		delta=fmt.money(totals['variance']),
		help='Target minus spending. Negative means this period is over its plan.',
	)
with used:
	fmt.stat(
		'Target used',
		fmt.percent(totals['used']),
		help='Spending as a share of the whole period’s target',
	)

if result.in_progress:
	st.caption(
		f'{result.elapsed_share:.0%} of the way through this period — the plan allows '
		f'{fmt.money(totals["expected"])} by now, and at the rate so far this period finishes '
		f'at {fmt.money(totals["projected"])}.'
	)

st.divider()

# --- Needs attention ---------------------------------------------------------------------

attention = result.needs_attention

st.subheader('Needs attention')

if attention.empty:
	st.success('Every budget is inside its target for this period.')
else:
	over = result.with_status('over')
	unplanned = result.with_status(variance.UNPLANNED)

	notes = []
	if not over.empty:
		notes.append(
			f'**{len(over)}** over target by **{fmt.money(-over["variance"].sum())}**'
		)
	if not unplanned.empty:
		notes.append(f'**{fmt.money(unplanned["actual"].sum())}** spent against no plan')
	st.markdown('  •  '.join(notes))

	st.dataframe(
		for_display(attention)[['name', 'category', 'target', 'actual', 'variance', 'status']],
		hide_index=True,
		width='stretch',
		column_config=COLUMNS,
	)

st.divider()

# --- Comparison --------------------------------------------------------------------------

st.subheader('Every budget')

target_column = 'target'

if result.in_progress:
	basis = st.radio(
		'Compare against',
		['Whole period', 'Expected by now'],
		horizontal=True,
		key='basis',
		help='This period has not finished, so the whole target is not due yet.',
	)
	if basis == 'Expected by now':
		target_column = 'expected'

st.plotly_chart(
	fmt.progress_bars(result.rows, 'name', 'actual', target_column, 'status'),
	width='stretch',
)

# --- Detail ------------------------------------------------------------------------------

# The pacing columns only mean something while the period is still running.
detail_columns = ['name', 'category', 'target', 'actual', 'variance', 'used']
if result.in_progress:
	detail_columns += ['expected', 'projected']
detail_columns += ['status']

by_budget_tab, by_category_tab = st.tabs(['By budget', 'By category'])

with by_budget_tab:
	st.dataframe(
		for_display(result.rows)[detail_columns],
		hide_index=True,
		width='stretch',
		column_config=COLUMNS,
	)

with by_category_tab:
	st.caption('The same comparison rolled up to the tags on each budget.')
	st.dataframe(
		for_display(categories(start_date, end_date, takehome))[
			[c for c in detail_columns if c != 'name']
		],
		hide_index=True,
		width='stretch',
		column_config=COLUMNS,
	)
