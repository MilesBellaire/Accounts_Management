import sqlite3

import pandas as pd

import config
from database.io.lock import write_lock
from database.io.budget import budget
from database.io.income import income
from database.io.statement import statement
from database.io.budget_balance import budget_balance
from database.io.transaction import transaction


class Database:
	def __init__(self, db_path):
		self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
		self._cursor = self._conn.cursor()

		self.budget = budget(self._conn)
		self.income = income(self._conn)
		self.statement = statement(self._conn)
		self.budget_balance = budget_balance(self._conn)
		self.transaction = transaction(self._conn)

	def close(self):
		self._conn.close()

	def get_keyword(self, budget_id=None, income_id=None):
		sql_query = """
			select
				k.rowid as id,
				k.text,
				k.budget_id,
				k.income_id
			from keyword k
		"""
		params = []

		if budget_id:
			sql_query += "where k.budget_id = ?"
			params.append(budget_id)
		elif income_id:
			sql_query += "where k.income_id = ?"
			params.append(income_id)

		return pd.read_sql_query(sql_query, self._conn, params=params)

	def insert_keyword(self, text, budget_id=None, income_id=None):
		with write_lock:
			self._cursor.execute(
				"insert into keyword(text, budget_id, income_id) values (?, ?, ?);",
				(text, budget_id, income_id),
			)
			self._conn.commit()

		return self._cursor.lastrowid

	def delete_keyword(self, id):
		with write_lock:
			self._cursor.execute("delete from keyword where rowid = ?;", (id,))
			self._conn.commit()

	def get_constants(self):
		return pd.read_sql_query("select rowid as id, name, value from constants;", self._conn)

	def insert_constant(self, name, value):
		with write_lock:
			self._cursor.execute(
				"insert into constants(name, value) values (?, ?);",
				(name, value),
			)
			self._conn.commit()

		return self._cursor.lastrowid

	def update_constant(self, id, name, value):
		with write_lock:
			self._cursor.execute(
				"update constants set name = ?, value = ? where rowid = ?;",
				(name, value, id),
			)
			self._conn.commit()

	def delete_constant(self, id):
		with write_lock:
			self._cursor.execute("delete from constants where rowid = ?;", (id,))
			self._conn.commit()

	def get_transactions_by_income(self):
		sql_query = """
			select i.id, i.name, sum(amount) as credit
			from transact t
			join income i on t.income_id = i.id
			where is_transfer = 0
			group by i.id, i.name;
		"""
		return pd.read_sql_query(sql_query, self._conn)

	def update_distribution_weight(self, income_id, budget_id, weight):
		sql_query = """
			update distribution_budget
			set weight = ?
			where distribution_id = (select primary_distribution_id from income where id = ?)
				and budget_id = ?;
		"""
		with write_lock:
			self._cursor.execute(sql_query, (weight, income_id, budget_id))
			self._conn.commit()

	def get_tracking_types(self):
		return pd.read_sql_query("select * from tracking_type;", self._conn)

	def get_accounts(self):
		return pd.read_sql_query("select * from account;", self._conn)

	def insert_distribution_budget(self, income_id, budget_id):
		sql_query = """
			insert into distribution_budget(distribution_id, budget_id, weight)
			select primary_distribution_id, ?, 0
			from income where id = ?;
		"""
		with write_lock:
			self._cursor.execute(sql_query, (budget_id, income_id))
			self._conn.commit()

		return self._cursor.lastrowid

	def get_transact_amount_by_income(self, income_id):
		sql_query = """
			select sum(amount) from transact
			where distribution_id in (
				select id
				from distribution
				where income_id = ?
			);
		"""
		return pd.read_sql_query(sql_query, self._conn, params=[income_id])

	def get_transact_amount_by_budget(self, budget_id):
		sql_query = """
			select sum(amount) from transact
			where distribution_id in (
				select id
				from distribution
				where budget_id = ?
			);
		"""
		return pd.read_sql_query(sql_query, self._conn, params=[budget_id])

	def get_account_balance_diffs(self):
		return pd.read_sql_query("select * from account_sys_diff;", self._conn)


sql = Database(config.DB_PATH)
