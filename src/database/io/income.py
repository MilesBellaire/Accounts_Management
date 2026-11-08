import pandas as pd

from database.io.lock import write_lock
from database.io.util import nullable


class income:
	def __init__(self, conn):
		self._conn = conn
		self._cursor = conn.cursor()

	def get(self):
		sql_query = """
			select
				i.name,
				i.value,
				u.abv as unit,
				i.equation,
				i.tags,
				t.name as tracking_type,
				ifnull(GROUP_CONCAT(b.name, ', '), '') as budgets,
				i.id
			from income i
			join tracking_type t on i.tracking_type_id = t.id
			join income_unit u on i.unit_id = u.id
			left join distribution d on i.primary_distribution_id = d.id
			left join distribution_budget db on d.id = db.distribution_id
			left join budget b on db.budget_id = b.id
			group by i.id, i.name, i.value, u.abv, i.equation, i.tags, t.name
		"""
		return pd.read_sql_query(sql_query, self._conn)

	def get_id_by_keyword(self, text):
		sql_query = """
			select
				GROUP_CONCAT(k.text, ', ') as text,
				k.income_id as id,
				i.name
			from keyword k
			join income i on k.income_id = i.id
			where ? like '%'||k.text||'%'
			group by k.income_id, i.name
		"""
		return pd.read_sql_query(sql_query, self._conn, params=[text])

	def get_units(self):
		return pd.read_sql_query("select * from income_unit;", self._conn)

	def insert(self, name, equation, tags, tracking_type_id, unit_id, value, budget_ids):
		create_income = """
			insert into income(name, equation, tags, tracking_type_id, unit_id, value)
			values (?, ?, ?, ?, ?, ?);
		"""
		create_distribution = """
			insert into distribution(name, income_id)
			select 'primary', i.id
			from income i
			where i.id = ?;
		"""
		update_income_with_distribution = """
			update income
			set primary_distribution_id = ?
			where id = ?;
		"""
		create_distribution_budget = """
			insert into distribution_budget(distribution_id, budget_id, weight)
			select ?, ?, 0
			from budget
			where id = ?;
		"""

		with write_lock:
			self._cursor.execute(
				create_income,
				(
					name,
					nullable(equation),
					tags,
					nullable(tracking_type_id),
					nullable(unit_id),
					nullable(value),
				),
			)
			new_income_id = self._cursor.lastrowid

			self._cursor.execute(create_distribution, (new_income_id,))
			new_distribution_id = self._cursor.lastrowid

			self._cursor.execute(update_income_with_distribution, (new_distribution_id, new_income_id))

			for budget_id in budget_ids:
				self._cursor.execute(
					create_distribution_budget,
					(new_distribution_id, nullable(budget_id), nullable(budget_id)),
				)

			self._conn.commit()

		return new_income_id

	def update(self, income_id, name, equation, tags, tracking_type_id, unit_id, value, budget_ids):
		update_income = """
			update income
			set name = ?,
				equation = ?,
				tags = ?,
				tracking_type_id = ?,
				unit_id = ?,
				value = ?
			where id = ?;
		"""
		delete_distribution_budget = """
			delete from distribution_budget
			where distribution_id in (
				select d.id
				from distribution d
				join income i on d.id = i.primary_distribution_id
				where i.id = ?
			);
		"""
		create_distribution_budget = """
			insert into distribution_budget(distribution_id, budget_id, weight)
			select (select primary_distribution_id from income where id = ?), ?, 0
			from budget
			where id = ?;
		"""

		with write_lock:
			self._cursor.execute(
				update_income,
				(
					name,
					nullable(equation),
					tags,
					nullable(tracking_type_id),
					nullable(unit_id),
					nullable(value),
					nullable(income_id),
				),
			)
			self._cursor.execute(delete_distribution_budget, (income_id,))

			for budget_id in budget_ids:
				self._cursor.execute(
					create_distribution_budget,
					(nullable(income_id), nullable(budget_id), nullable(budget_id)),
				)

			self._conn.commit()

	def delete(self, income_id):
		delete_distribution_budget = """
			delete from distribution_budget
			where distribution_id in (
				select id
				from distribution
				where income_id = ?
			);
		"""

		with write_lock:
			self._cursor.execute("delete from income where id = ?;", (income_id,))
			self._cursor.execute(delete_distribution_budget, (income_id,))
			self._cursor.execute("delete from distribution where income_id = ?;", (income_id,))
			self._cursor.execute("update transact set income_id = -1 where income_id = ?;", (income_id,))
			self._conn.commit()
