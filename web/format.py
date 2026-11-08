"""Formatting and chart styling shared by every page.

Colors come from the validated categorical palette; slots are assigned in fixed order and
never cycled, so an account keeps its color as filters change.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Categorical slots, in the fixed order the palette defines. Bars use the adjacent pairlist,
# so slots 1-8 are in play; anything scatter-like is capped at the first three.
SERIES_LIGHT = [
	'#2a78d6', '#eb6834', '#1baf7a', '#eda100',
	'#e87ba4', '#008300', '#4a3aa7', '#e34948',
]
SERIES_DARK = [
	'#3987e5', '#d95926', '#199e70', '#c98500',
	'#d55181', '#008300', '#9085e9', '#e66767',
]

INK = {
	'light': {
		'surface': '#fcfcfb',
		'primary': '#0b0b0b',
		'secondary': '#52514e',
		'muted': '#898781',
		'grid': '#e1e0d9',
		'axis': '#c3c2b7',
	},
	'dark': {
		'surface': '#1a1a19',
		'primary': '#ffffff',
		'secondary': '#c3c2b7',
		'muted': '#898781',
		'grid': '#2c2c2a',
		'axis': '#383835',
	},
}

STATUS = {'good': '#0ca30c', 'warning': '#fab219', 'serious': '#ec835a', 'critical': '#d03b3b'}


def theme() -> str:
	"""'light' or 'dark', following whatever the viewer has Streamlit set to."""
	try:
		return st.context.theme.type or 'light'
	except Exception:
		return 'light'


def ink():
	return INK[theme()]


def series_colors():
	return SERIES_DARK if theme() == 'dark' else SERIES_LIGHT


def color_map(names):
	"""Fixed name -> color assignment, so a color follows the entity and not its rank."""
	colors = series_colors()
	return {name: colors[i % len(colors)] for i, name in enumerate(sorted(map(str, names)))}


# --- Text formatting --------------------------------------------------------------------

def pretty(name):
	"""Display form of a stored name: 'car_insurance' -> 'Car Insurance'.

	Only the first letter of each word is touched, so deliberate casing survives
	('PreDeposit' stays as it is) and so does a leading digit ('401k' does not become '401K').
	Storage always uses the raw lowercase name; this is for tables and charts only.
	"""
	if name is None:
		return name
	try:
		if pd.isna(name):
			return name
	except (TypeError, ValueError):
		pass

	words = str(name).replace('_', ' ').split()
	return ' '.join(w[0].upper() + w[1:] if w[0].isalpha() else w for w in words)


def pretty_series(series):
	return series.map(pretty)


def pretty_list(names):
	return [pretty(n) for n in names]


def unpretty_map(names):
	"""Pretty label -> the stored name, for reading a selection back out of a widget."""
	return {pretty(n): n for n in names}


def _is_missing(value) -> bool:
	"""A NaN reaching a label means "not applicable" - an unplanned budget has no share of a
	target to report - so it is shown as a dash rather than as the string 'nan'."""
	try:
		return bool(pd.isna(value))
	except (TypeError, ValueError):
		return False


def money(value) -> str:
	if value is None:
		return ''
	if _is_missing(value):
		return '—'
	try:
		return f'-${abs(value):,.2f}' if value < 0 else f'${value:,.2f}'
	except (TypeError, ValueError):
		return str(value)


def percent(value) -> str:
	if value is None or _is_missing(value):
		return '—'
	try:
		return f'{value:.2%}'
	except (TypeError, ValueError):
		return str(value)


def money_label(value, cents=False) -> str:
	"""Short money string for a mark label; cents only when the values are small."""
	try:
		return f'-${abs(value):,.{2 if cents else 0}f}' if value < 0 else f'${value:,.{2 if cents else 0}f}'
	except (TypeError, ValueError):
		return str(value)


def money_column(label=None, help=None):
	return st.column_config.NumberColumn(label, format='dollar', help=help)


def percent_column(label=None):
	return st.column_config.NumberColumn(label, format='percent')


# --- Charts -----------------------------------------------------------------------------

def style_axes(fig, x_title=None, y_title=None, show_x_grid=True, show_y_grid=False):
	"""Hairline, recessive grid and axes; solid, never dashed."""
	palette = ink()

	fig.update_layout(
		paper_bgcolor='rgba(0,0,0,0)',
		plot_bgcolor='rgba(0,0,0,0)',
		font=dict(
			family='system-ui, -apple-system, "Segoe UI", sans-serif',
			color=palette['secondary'],
			size=13,
		),
		margin=dict(l=8, r=24, t=8, b=8, autoexpand=True),
		hoverlabel=dict(
			bgcolor=palette['surface'],
			bordercolor=palette['axis'],
			font=dict(color=palette['primary'], size=13),
		),
		legend=dict(
			orientation='h',
			yanchor='bottom',
			y=1.02,
			x=0,
			title_text='',
			font=dict(color=palette['secondary']),
		),
	)
	# automargin lets plotly grow the margin to fit tick labels; without it the category
	# names and axis values are clipped away entirely.
	fig.update_xaxes(
		title_text=x_title,
		showgrid=show_x_grid,
		gridcolor=palette['grid'],
		gridwidth=1,
		griddash='solid',
		zeroline=True,
		zerolinecolor=palette['axis'],
		zerolinewidth=1,
		linecolor=palette['axis'],
		tickcolor=palette['axis'],
		tickfont=dict(color=palette['muted']),
		automargin=True,
	)
	fig.update_yaxes(
		title_text=y_title,
		showgrid=show_y_grid,
		gridcolor=palette['grid'],
		gridwidth=1,
		griddash='solid',
		zeroline=False,
		linecolor=palette['axis'],
		tickcolor=palette['axis'],
		tickfont=dict(color=palette['muted']),
		automargin=True,
	)
	return fig


def horizontal_bars(df, label_column, value_column, color_column=None, height=None):
	"""Magnitude across named categories - the default form for balances by budget/account.

	Bars are ordered by value, colored by `color_column` when identity matters, and carry a
	hover tooltip. A legend appears whenever more than one color class is present.
	"""
	palette = ink()
	groups = []

	# Grouping the bars by color class keeps each one in a contiguous block, so two hues only
	# meet at a group boundary rather than alternating down the chart. Groups run largest
	# first, matching how the sections are ordered elsewhere. Plotly draws the first category
	# at the bottom, so the frame is built bottom-up and reversed for display.
	if color_column is None:
		df = df.sort_values(value_column)
	else:
		totals = df.groupby(color_column)[value_column].sum().sort_values()
		groups = totals.index.tolist()
		rank = {name: i for i, name in enumerate(groups)}
		df = (
			df.assign(_rank=df[color_column].map(rank))
			.sort_values(['_rank', value_column])
			.drop(columns='_rank')
		)

	# Labels are display text, so they carry the pretty form of the stored name.
	df = df.copy()
	df[label_column] = pretty_series(df[label_column])
	if color_column is not None:
		df[color_column] = pretty_series(df[color_column])

	# Cents only help when the values are small; above that they are noise on a bar label.
	cents = df[value_column].abs().max() < 100
	palette_text = palette['secondary']

	fig = go.Figure()

	def add(group, name=None, color=None):
		fig.add_bar(
			x=group[value_column],
			y=group[label_column].astype(str),
			orientation='h',
			name=name,
			marker=dict(color=color, cornerradius=4),
			hovertemplate=(
				'%{y}<br>' + (name + '<br>' if name else '') + '%{customdata}<extra></extra>'
			),
			customdata=[money(v) for v in group[value_column]],
			# Value labels sit past the end of each bar, in text ink rather than the series color.
			text=[money_label(v, cents) for v in group[value_column]],
			textposition='outside',
			textfont=dict(color=palette_text, size=12),
			cliponaxis=False,
			showlegend=name is not None,
		)

	if color_column is None:
		add(df, color=series_colors()[0])
	else:
		# Colors are keyed on the sorted names so a group keeps its hue as filters change,
		# while the traces are added top-down so the legend reads in the order shown.
		colors = color_map(pretty_list(groups))
		for name in reversed(pretty_list(groups)):
			add(df[df[color_column].astype(str) == name], name=name, color=colors[name])

	fig.update_layout(
		barmode='stack',
		bargap=0.35,
		height=height or max(220, 26 * len(df) + 90),
		showlegend=color_column is not None and df[color_column].nunique() > 1,
		# Stacked bars default to a reversed legend; 'normal' puts the legend back in the
		# order the reader meets the groups going down the chart.
		legend=dict(traceorder='normal'),
	)
	style_axes(fig, x_title=None, y_title=None)
	# Headroom so the outside value labels are not clipped at the right edge.
	span = max(df[value_column].max(), 0) - min(df[value_column].min(), 0)
	fig.update_xaxes(
		tickprefix='$',
		tickformat=',.0f',
		range=[min(df[value_column].min(), 0), max(df[value_column].max(), 0) + span * 0.16],
	)
	fig.update_yaxes(categoryorder='array', categoryarray=df[label_column].astype(str).tolist())
	fig.update_traces(marker_line_width=0)

	return fig


def stat(label: str, value: str, help: str = None, delta=None, delta_color='normal'):
	st.metric(label, value, delta=delta, delta_color=delta_color, help=help)


# --- Variance ---------------------------------------------------------------------------

# Plan-vs-actual statuses. Color carries severity here rather than identity, because the
# question a variance chart answers is "which of these is a problem", not "which budget is
# this" - so these come from STATUS and not from the categorical series palette.
VARIANCE_COLORS = {
	'over': STATUS['critical'],
	'unplanned': STATUS['serious'],
	'near': STATUS['warning'],
	'under': STATUS['good'],
}

VARIANCE_LABELS = {
	'over': 'Over',
	'unplanned': 'Unplanned',
	'near': 'Close to target',
	'under': 'Under',
}


def progress_bars(df, label_column, actual_column, target_column, status_column, height=None):
	"""Spending against its target, one row per budget.

	The bar is what was spent, colored by status; the tick is what the plan allows. Rows are
	drawn in the order given, so the caller decides what the reader meets first.
	"""
	palette = ink()

	# Plotly draws the first category at the bottom, so the frame is reversed to make the
	# caller's first row appear at the top.
	df = df.iloc[::-1].copy()
	df[label_column] = pretty_series(df[label_column]).astype(str)

	cents = df[[actual_column, target_column]].abs().to_numpy().max(initial=0) < 100

	fig = go.Figure()

	for status in VARIANCE_COLORS:
		group = df[df[status_column] == status]
		if group.empty:
			continue

		fig.add_bar(
			x=group[actual_column],
			y=group[label_column],
			orientation='h',
			name=VARIANCE_LABELS[status],
			marker=dict(color=VARIANCE_COLORS[status], cornerradius=4),
			customdata=[
				[money(a), money(t)]
				for a, t in zip(group[actual_column], group[target_column])
			],
			hovertemplate='%{y}<br>Spent %{customdata[0]}<br>Target %{customdata[1]}<extra></extra>',
			text=[money_label(v, cents) for v in group[actual_column]],
			textposition='outside',
			textfont=dict(color=palette['secondary'], size=12),
			cliponaxis=False,
		)

	# The target sits on the same row as the bar, as a tick rather than a second bar: it is a
	# threshold to read the bar against, not another quantity to compare lengths of.
	fig.add_scatter(
		x=df[target_column],
		y=df[label_column],
		mode='markers',
		name='Target',
		marker=dict(
			symbol='line-ns',
			size=16,
			line=dict(color=palette['primary'], width=2),
		),
		hovertemplate='%{y}<br>Target %{x:$,.2f}<extra></extra>',
	)

	fig.update_layout(
		barmode='overlay',
		bargap=0.35,
		height=height or max(220, 26 * len(df) + 90),
		showlegend=True,
		legend=dict(traceorder='normal'),
	)
	style_axes(fig)

	# Headroom so the outside value labels are not clipped at the right edge.
	span = max(df[actual_column].max(), df[target_column].max(), 0)
	fig.update_xaxes(tickprefix='$', tickformat=',.0f', range=[0, span * 1.16])
	fig.update_yaxes(categoryorder='array', categoryarray=df[label_column].tolist())

	return fig


# --- Over time --------------------------------------------------------------------------

# A folded tail is not a series, so it does not get a categorical hue.
OTHER_COLOR = {'light': '#a8a69e', 'dark': '#6b6a65'}


def time_color_map(names):
	"""Colors for a set of series over time, with the folded tail held back to gray.

	Assignment is by sorted name rather than by size, so a series keeps its color as the
	months in view change.
	"""
	real = sorted(str(n) for n in names if str(n) != 'other')
	colors = color_map(real)
	colors['other'] = OTHER_COLOR[theme()]
	return colors


def _time_axis(fig, height, percent, series_count):
	palette = ink()

	fig.update_layout(
		height=height or 360,
		# One crosshair tooltip for the whole month beats hunting for each mark.
		hovermode='x unified',
		showlegend=series_count > 1,
		legend=dict(traceorder='normal'),
	)
	style_axes(fig, show_x_grid=False, show_y_grid=True)

	if percent:
		fig.update_yaxes(tickformat='.0%', range=[0, 1])
	else:
		fig.update_yaxes(tickprefix='$', tickformat=',.0f')

	# 'YYYY-MM' is about as wide as a two-year axis gives each tick, so past a year of them
	# the labels are angled rather than left to collide. automargin makes the room.
	ticks = {
		value for trace in fig.data
		for value in (trace.x if trace.x is not None else ())
	}
	fig.update_xaxes(
		type='category',
		tickcolor=palette['axis'],
		tickangle=-45 if len(ticks) > 12 else 0,
	)
	return fig


def stacked_columns(df, x_column, value_column, series_column, height=None, percent=False):
	"""Part-to-whole across successive months.

	Series are drawn in sorted order so the stack does not reshuffle between months, and each
	segment carries a surface-colored edge, which reads as a hairline gap between fills.
	"""
	palette = ink()
	colors = time_color_map(df[series_column].unique())

	fig = go.Figure()

	# 'other' last, so the tail sits at the top of the stack rather than in the middle of it.
	names = sorted(str(n) for n in df[series_column].unique() if str(n) != 'other')
	if 'other' in df[series_column].astype(str).values:
		names.append('other')

	for name in names:
		group = df[df[series_column].astype(str) == name]
		fig.add_bar(
			x=group[x_column],
			y=group[value_column],
			name=pretty(name),
			marker=dict(
				color=colors[name],
				cornerradius=4,
				# A 2px surface-colored edge is what separates one fill from the next.
				line=dict(color=palette['surface'], width=2),
			),
			hovertemplate=(
				'%{y:.1%}<extra>' + pretty(name) + '</extra>' if percent
				else '%{y:$,.2f}<extra>' + pretty(name) + '</extra>'
			),
		)

	fig.update_layout(barmode='stack', bargap=0.3)
	return _time_axis(fig, height, percent, len(names))


def lines(df, x_column, value_column, series_column, height=None, percent=False):
	"""Trend over time for a handful of series.

	Lines are for identity over time, so this is capped by the caller: past three or four
	series a stack or a set of small multiples reads better than a bowl of spaghetti.
	"""
	colors = time_color_map(df[series_column].unique())
	names = sorted(str(n) for n in df[series_column].unique())

	fig = go.Figure()

	for name in names:
		group = df[df[series_column].astype(str) == name].sort_values(x_column)
		fig.add_scatter(
			x=group[x_column],
			y=group[value_column],
			mode='lines+markers',
			name=pretty(name),
			line=dict(color=colors[name], width=2),
			marker=dict(size=8, line=dict(width=0)),
			hovertemplate=(
				'%{y:.1%}<extra>' + pretty(name) + '</extra>' if percent
				else '%{y:$,.2f}<extra>' + pretty(name) + '</extra>'
			),
		)

	fig = _time_axis(fig, height, percent, len(names))
	if not percent:
		# A balance can go negative, so the zero line has to be visible.
		fig.update_yaxes(zeroline=True, zerolinecolor=ink()['axis'], zerolinewidth=1, range=None)
	return fig
