"""Write-path tests against a disposable copy of the database.

These exercise statement insert -> stage -> delete, including the transact triggers that
clone an income's distribution. The real db.db is copied first and never written to.
"""

import shutil

import pandas as pd
import pytest

import config
from database.io.dbio import Database


@pytest.fixture
def db(tmp_path):
	"""A throwaway copy of the real database."""
	if not config.DB_PATH.exists():
		pytest.skip('no database to copy')

	copy_path = tmp_path / 'copy.db'
	shutil.copy(config.DB_PATH, copy_path)

	database = Database(copy_path)
	yield database
	database.close()


def a_transaction(db, description, amount, debit_or_credit, statement_id):
	"""One row shaped the way the parser + categorizer hand it to stage_transactions."""
	budgets = db.budget.get()
	incomes = db.income.get()
	accounts = db.get_accounts()

	if debit_or_credit == '-':
		category = budgets.iloc[0]
	else:
		category = incomes.iloc[0]

	return {
		'Date': pd.Timestamp('2025-06-15'),
		'Description': description,
		'DebitOrCredit': debit_or_credit,
		'Amount': amount,
		'Account': accounts.iloc[0]['number'],
		'Category': category['name'],
		'AssociatedId': category['id'],
		'IsTransfer': 0,
		'StatementId': statement_id,
	}


def test_stage_and_delete_roundtrip(db):
	before = len(db.transaction.get())

	statement_id = db.statement.insert(
		'pytest-throwaway', pd.Timestamp('2025-06-01'), pd.Timestamp('2025-06-30')
	)
	rows = pd.DataFrame([
		a_transaction(db, 'pytest debit', 12.34, '-', statement_id),
		a_transaction(db, 'pytest credit', 56.78, '+', statement_id),
	])
	db.statement.stage_transactions(rows)

	staged = db.transaction.get(statement_id=statement_id)
	assert len(staged) == 2
	assert len(db.transaction.get()) == before + 2

	db.statement.delete(statement_id)

	assert len(db.transaction.get(statement_id=statement_id)) == 0
	assert len(db.transaction.get()) == before
	assert db.statement.exists('pytest-throwaway') == 0


def test_credit_gets_a_distribution(db):
	"""The insert trigger should clone the income's distribution onto a credit."""
	statement_id = db.statement.insert(
		'pytest-distribution', pd.Timestamp('2025-06-01'), pd.Timestamp('2025-06-30')
	)
	rows = pd.DataFrame([a_transaction(db, 'pytest credit', 100.0, '+', statement_id)])
	db.statement.stage_transactions(rows)

	staged = db.transaction.get(statement_id=statement_id)
	distribution_id = pd.read_sql_query(
		'select distribution_id from transact where id = ?',
		db._conn,
		params=[int(staged.iloc[0]['id'])],
	).iloc[0]['distribution_id']

	assert distribution_id is not None

	db.statement.delete(statement_id)


def test_apostrophe_in_budget_name_is_parameterized(db):
	"""A name with a quote used to break the f-string SQL in budget.insert."""
	units = db.budget.get_units()
	tracking_types = db.get_tracking_types()
	accounts = db.get_accounts()

	new_id = db.budget.insert(
		"o'brien's fund",
		None,
		"tag's",
		int(tracking_types.iloc[0]['id']),
		int(units.iloc[0]['id']),
		10.0,
		None,
		int(accounts.iloc[0]['id']),
	)

	assert new_id
	assert "o'brien's fund" in db.budget.get()['name'].tolist()

	db.budget.update(
		new_id,
		"o'brien's other fund",
		None,
		'',
		int(tracking_types.iloc[0]['id']),
		int(units.iloc[0]['id']),
		20.0,
		None,
		int(accounts.iloc[0]['id']),
	)

	assert "o'brien's other fund" in db.budget.get()['name'].tolist()

	db.budget.delete(new_id)

	assert "o'brien's other fund" not in db.budget.get()['name'].tolist()


def test_nan_cap_becomes_null(db):
	"""float('nan') is truthy, so a NaN cap used to be written into the SQL literally."""
	units = db.budget.get_units()
	tracking_types = db.get_tracking_types()
	accounts = db.get_accounts()

	new_id = db.budget.insert(
		'pytest-nan-cap',
		None,
		'',
		int(tracking_types.iloc[0]['id']),
		int(units.iloc[0]['id']),
		5.0,
		float('nan'),
		int(accounts.iloc[0]['id']),
	)

	cap = pd.read_sql_query(
		'select cap from budget where id = ?', db._conn, params=[new_id]
	).iloc[0]['cap']

	assert pd.isna(cap)

	db.budget.delete(new_id)


def test_income_insert_returns_the_income_id(db):
	"""It used to return the last distribution_budget rowid instead."""
	units = db.income.get_units()
	tracking_types = db.get_tracking_types()
	budgets = db.budget.get()

	new_id = db.income.insert(
		'pytest-income',
		None,
		'',
		int(tracking_types.iloc[0]['id']),
		int(units.iloc[0]['id']),
		100.0,
		[int(budgets.iloc[0]['id'])],
	)

	stored = db.income.get()
	assert new_id in stored['id'].tolist()
	assert stored[stored['id'] == new_id].iloc[0]['name'] == 'pytest-income'

	db.income.delete(new_id)


def test_keyword_roundtrip(db):
	"""get_keyword/delete_keyword used to select a column the keyword table doesn't have."""
	budgets = db.budget.get()
	budget_id = int(budgets.iloc[0]['id'])

	new_id = db.insert_keyword('pytest-keyword', budget_id=budget_id)
	stored = db.get_keyword(budget_id=budget_id)

	assert 'pytest-keyword' in stored['text'].tolist()

	db.delete_keyword(new_id)

	assert 'pytest-keyword' not in db.get_keyword(budget_id=budget_id)['text'].tolist()


def test_constants_roundtrip(db):
	new_id = db.insert_constant('pytest_constant', 1.5)

	assert 'pytest_constant' in db.get_constants()['name'].tolist()

	db.update_constant(new_id, 'pytest_constant', 2.5)
	stored = db.get_constants()
	assert stored[stored['id'] == new_id].iloc[0]['value'] == 2.5

	db.delete_constant(new_id)
	assert 'pytest_constant' not in db.get_constants()['name'].tolist()
