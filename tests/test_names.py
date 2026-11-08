"""Display names.

Stored names are lowercase with underscores; tables and charts show a prettified form.
Anywhere the user picks a pretty label that has to be written back (the Transactions editor,
the Statements categorizer), the mapping has to be reversible - hence the injectivity tests.
"""

import pytest

import format as fmt
from database.io.dbio import sql


@pytest.mark.parametrize(
	'stored, shown',
	[
		('car_insurance', 'Car Insurance'),
		('groceries', 'Groceries'),
		('medical insurance', 'Medical Insurance'),
		('self_care', 'Self Care'),
		('401k', '401k'),
		('PreDeposit', 'PreDeposit'),
		('sporting_equipment', 'Sporting Equipment'),
		('', ''),
	],
)
def test_pretty(stored, shown):
	assert fmt.pretty(stored) == shown


def test_pretty_passes_through_none():
	assert fmt.pretty(None) is None


def test_pretty_does_not_uppercase_after_a_digit():
	"""str.title() would turn '401k' into '401K'."""
	assert fmt.pretty('401k_match') == '401k Match'


@pytest.mark.parametrize('table', ['budget', 'income'])
def test_pretty_is_reversible_for_real_names(table):
	"""Two names must not prettify to the same label, or a save could pick the wrong record."""
	names = getattr(sql, table).get()['name'].tolist()
	shown = [fmt.pretty(n) for n in names]

	assert len(set(shown)) == len(names), f'collision in {table}: {shown}'


@pytest.mark.parametrize('table', ['budget', 'income'])
def test_unpretty_map_round_trips(table):
	names = getattr(sql, table).get()['name'].tolist()
	back = fmt.unpretty_map(names)

	for name in names:
		assert back[fmt.pretty(name)] == name
