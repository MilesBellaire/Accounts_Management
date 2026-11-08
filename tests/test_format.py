"""The chart builders.

A chart that renders wrong fails silently - the page still loads - so the encodings that
carry meaning are asserted here: one color per series, the stack adding up, the percentage
axis bounded, and the month labels angled before they can collide.
"""

import pandas as pd
import pytest

import format as fmt


def series(names, months=('2026-01', '2026-02')):
	return pd.DataFrame(
		[(month, name, 100.0 + i) for i, name in enumerate(names) for month in months],
		columns=['month', 'name', 'amount'],
	)


def colors_of(fig):
	return [
		t.marker.color if t.type == 'bar' else t.line.color
		for t in fig.data
	]


# --- Money and percent formatting --------------------------------------------------------

@pytest.mark.parametrize('value, expected', [
	(0, '$0.00'), (12.5, '$12.50'), (-12.5, '-$12.50'), (1234567, '$1,234,567.00'),
	(None, ''), (float('nan'), '—'),
])
def test_money(value, expected):
	assert fmt.money(value) == expected


@pytest.mark.parametrize('value, expected', [
	(0.5, '50.00%'), (0, '0.00%'), (None, '—'), (float('nan'), '—'),
])
def test_percent(value, expected):
	assert fmt.percent(value) == expected


def test_pretty_leaves_deliberate_casing_and_leading_digits_alone():
	assert fmt.pretty('car_insurance') == 'Car Insurance'
	assert fmt.pretty('401k') == '401k'
	assert fmt.pretty('PreDeposit') == 'PreDeposit'


# --- Stacked columns ---------------------------------------------------------------------

def test_every_series_gets_its_own_color():
	fig = fmt.stacked_columns(series(list('abcdefg')), 'month', 'amount', 'name')

	assert len(set(colors_of(fig))) == len(fig.data)


def test_the_folded_tail_is_gray_rather_than_a_series_color():
	"""'other' is not a series, so it must not take a categorical slot."""
	fig = fmt.stacked_columns(series(['a', 'b', 'other']), 'month', 'amount', 'name')
	tail = next(t for t in fig.data if t.name == 'Other')

	assert tail.marker.color == fmt.OTHER_COLOR[fmt.theme()]
	assert tail.marker.color not in fmt.series_colors()


def test_the_tail_is_drawn_last_so_it_sits_on_top_of_the_stack():
	fig = fmt.stacked_columns(series(['other', 'a', 'b']), 'month', 'amount', 'name')

	assert [t.name for t in fig.data][-1] == 'Other'


def test_stacked_segments_carry_a_surface_gap():
	"""A 2px surface-colored edge is what separates one fill from the next."""
	fig = fmt.stacked_columns(series(list('ab')), 'month', 'amount', 'name')

	for trace in fig.data:
		assert trace.marker.line.width == 2
		assert trace.marker.line.color == fmt.ink()['surface']


def test_percent_mode_bounds_the_axis_and_formats_it():
	fig = fmt.stacked_columns(series(list('ab')), 'month', 'amount', 'name', percent=True)

	assert tuple(fig.layout.yaxis.range) == (0, 1)
	assert fig.layout.yaxis.tickformat == '.0%'
	assert fig.layout.yaxis.tickprefix is None


def test_amounts_mode_formats_the_axis_as_money():
	fig = fmt.stacked_columns(series(list('ab')), 'month', 'amount', 'name')

	assert fig.layout.yaxis.tickprefix == '$'


# --- The month axis ----------------------------------------------------------------------

def test_a_year_of_months_is_left_upright():
	months = [f'2026-{m:02d}' for m in range(1, 13)]
	fig = fmt.stacked_columns(series(['a'], months), 'month', 'amount', 'name')

	assert fig.layout.xaxis.tickangle == 0


def test_more_than_a_year_of_months_is_angled_before_the_labels_collide():
	months = [f'{y}-{m:02d}' for y in (2025, 2026) for m in range(1, 13)]
	fig = fmt.stacked_columns(series(['a'], months), 'month', 'amount', 'name')

	assert fig.layout.xaxis.tickangle == -45


# --- Lines -------------------------------------------------------------------------------

def test_lines_carry_the_mark_spec():
	fig = fmt.lines(series(list('abc')), 'month', 'amount', 'name')

	for trace in fig.data:
		assert trace.line.width == 2
		assert trace.marker.size >= 8


def test_lines_show_the_zero_line_because_a_balance_can_go_negative():
	fig = fmt.lines(series(list('ab')), 'month', 'amount', 'name')

	assert fig.layout.yaxis.zeroline
	assert fig.layout.yaxis.range is None


def test_a_lone_series_needs_no_legend():
	"""The title names it; a one-entry legend is noise."""
	assert not fmt.lines(series(['a']), 'month', 'amount', 'name').layout.showlegend
	assert fmt.lines(series(list('ab')), 'month', 'amount', 'name').layout.showlegend


def test_time_charts_hover_on_the_whole_month():
	fig = fmt.lines(series(list('ab')), 'month', 'amount', 'name')

	assert fig.layout.hovermode == 'x unified'


# --- Progress bars -----------------------------------------------------------------------

def test_progress_bars_color_by_status_not_identity():
	rows = pd.DataFrame({
		'name': ['rent', 'gas'],
		'actual': [1350.0, 40.0],
		'target': [1200.0, 100.0],
		'status': ['over', 'under'],
	})
	fig = fmt.progress_bars(rows, 'name', 'actual', 'target', 'status')
	bars = {t.name: t.marker.color for t in fig.data if t.type == 'bar'}

	assert bars['Over'] == fmt.STATUS['critical']
	assert bars['Under'] == fmt.STATUS['good']


def test_progress_bars_draw_a_target_tick_for_every_row():
	rows = pd.DataFrame({
		'name': ['rent', 'gas'],
		'actual': [1350.0, 40.0],
		'target': [1200.0, 100.0],
		'status': ['over', 'under'],
	})
	fig = fmt.progress_bars(rows, 'name', 'actual', 'target', 'status')
	ticks = next(t for t in fig.data if t.type == 'scatter')

	assert len(ticks.x) == 2


def test_progress_bars_put_the_first_row_at_the_top():
	"""Rows arrive worst-first; plotly draws the first category at the bottom."""
	rows = pd.DataFrame({
		'name': ['worst', 'middle', 'best'],
		'actual': [300.0, 200.0, 100.0],
		'target': [100.0, 200.0, 300.0],
		'status': ['over', 'near', 'under'],
	})
	fig = fmt.progress_bars(rows, 'name', 'actual', 'target', 'status')

	assert list(fig.layout.yaxis.categoryarray)[-1] == 'Worst'
