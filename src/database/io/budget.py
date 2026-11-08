import pandas as pd

from database.io.lock import write_lock
from database.io.util import nullable


class budget:

	def __init__(self, conn):
		self._conn = conn
		self._cursor = conn.cursor()

	def get(self):
		sql_query = """
			select
				b.name,
				b.value,
				u.abv as unit,
				b.cap,
				b.equation,
				b.tags,
				t.name as tracking_type,
				a.name as account,
				b.id
			from budget b
			join tracking_type t on b.tracking_type_id = t.id
			join budget_unit u on b.unit_id = u.id
			join account a on b.account_id = a.id
		"""

		return pd.read_sql_query(sql_query, self._conn)

	def get_id_by_keyword(self, text):
		sql_query = """
			select
				GROUP_CONCAT(k.text, ', ') as text,
				k.budget_id as id,
				b.name
			from keyword k
			join budget b on k.budget_id = b.id
			where ? like '%'||k.text||'%'
			group by k.budget_id, b.name
		"""
		return pd.read_sql_query(sql_query, self._conn, params=[text])

	def get_units(self):
		return pd.read_sql_query("select * from budget_unit;", self._conn)

	def insert(self, name, equation, tags, tracking_type_id, unit_id, value, cap, account_id):
		sql_query = """
			insert into budget(name, equation, tags, tracking_type_id, unit_id, value, cap, account_id)
			values (?, ?, ?, ?, ?, ?, ?, ?);
		"""
		with write_lock:
			self._cursor.execute(
				sql_query,
				(
					name,
					nullable(equation),
					tags,
					nullable(tracking_type_id),
					nullable(unit_id),
					nullable(value),
					nullable(cap),
					nullable(account_id),
				),
			)
			self._conn.commit()

		return self._cursor.lastrowid

	def update(self, budget_id, name, equation, tags, tracking_type_id, unit_id, value, cap, account_id):
		sql_query = """
			update budget
			set name = ?,
				equation = ?,
				tags = ?,
				tracking_type_id = ?,
				unit_id = ?,
				value = ?,
				cap = ?,
				account_id = ?
			where id = ?;
		"""
		with write_lock:
			self._cursor.execute(
				sql_query,
				(
					name,
					nullable(equation),
					tags,
					nullable(tracking_type_id),
					nullable(unit_id),
					nullable(value),
					nullable(cap),
					nullable(account_id),
					nullable(budget_id),
				),
			)
			self._conn.commit()

	def delete(self, budget_id):
		with write_lock:
			self._cursor.execute("delete from budget where id = ?;", (budget_id,))
			self._cursor.execute("delete from distribution_budget where budget_id = ?;", (budget_id,))
			self._cursor.execute("update transact set budget_id = -1 where budget_id = ?;", (budget_id,))
			self._conn.commit()
