"""Categorization tests with the keyword lookup stubbed out, so no database is involved."""

import pandas as pd
import pytest

from logic import categorize


def transactions(*rows):
	return pd.DataFrame(
		rows,
		columns=['Description', 'DebitOrCredit', 'IsTransfer', 'Category', 'AssociatedId'],
	)


def stub_matches(mapping):
	"""mapping: description -> list of (id, name) the keyword table would return."""

	def matcher(description, debit_or_credit):
		found = mapping.get(description, [])
		return pd.DataFrame(found, columns=['id', 'name'])

	return matcher


@pytest.fixture
def patch_matches(monkeypatch):
	def apply(mapping):
		monkeypatch.setattr(categorize, 'keyword_matches', stub_matches(mapping))

	return apply


def test_single_match_is_applied(patch_matches):
	patch_matches({'grocery mart': [(7, 'food')]})

	result = categorize.suggest_categories(transactions(('grocery mart', '-', 0, '', '')))

	assert result.iloc[0]['Category'] == 'food'
	assert result.iloc[0]['AssociatedId'] == 7


def test_multiple_matches_are_left_blank(patch_matches):
	"""Ambiguous rows are for a person to resolve, not for the matcher to guess."""
	patch_matches({'shell station': [(7, 'food'), (9, 'gas')]})

	result = categorize.suggest_categories(transactions(('shell station', '-', 0, '', '')))

	assert result.iloc[0]['Category'] == ''
	assert result.iloc[0]['AssociatedId'] == ''


def test_no_match_is_left_blank(patch_matches):
	patch_matches({})

	result = categorize.suggest_categories(transactions(('mystery vendor', '-', 0, '', '')))

	assert result.iloc[0]['Category'] == ''


def test_transfers_are_skipped(patch_matches):
	"""A transfer between the user's own accounts is neither income nor spending."""
	patch_matches({'online pmt': [(7, 'food')]})

	result = categorize.suggest_categories(transactions(('online pmt', '-', 1, '', '')))

	assert result.iloc[0]['Category'] == ''


def test_credits_match_against_incomes(patch_matches):
	seen = {}

	def matcher(description, debit_or_credit):
		seen['kind'] = debit_or_credit
		return pd.DataFrame([(3, 'salary')], columns=['id', 'name'])

	categorize.keyword_matches = matcher
	try:
		result = categorize.suggest_categories(transactions(('paycheck', '+', 0, '', '')))
	finally:
		import importlib

		importlib.reload(categorize)

	assert seen['kind'] == '+'
	assert result.iloc[0]['Category'] == 'salary'


def test_unresolved_lists_only_uncategorized(patch_matches):
	patch_matches({'grocery mart': [(7, 'food')]})

	result = categorize.suggest_categories(
		transactions(
			('grocery mart', '-', 0, '', ''),
			('mystery vendor', '-', 0, '', ''),
			('online pmt', '-', 1, '', ''),
		)
	)

	remaining = categorize.unresolved(result)

	assert list(remaining['Description']) == ['mystery vendor']
