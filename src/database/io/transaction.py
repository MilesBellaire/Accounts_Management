import pandas as pd

from database.io.lock import write_lock


class transaction:
	def __init__(self, conn):
		self._conn = conn
		self._cursor = conn.cursor()

	def get(
		self,
		start_date=None,
		end_date=None,
		account_id=None,
		budget_id=None,
		income_id=None,
		statement_id=None,
		search=None,
		is_transfer=None,
	):
		"""Transactions joined to their budget/income/account/statement names.

		Every filter is optional; passing none returns the full table.
		"""
		sql_query = """
			select
				t.id,
				t.date,
				t.insert_date,
				t.description,
				t.debit_or_credit,
				t.amount,
				t.class,
				b.name as budget,
				i.name as income,
				a.name as account,
				s.name as statement,
				t.is_transfer,
				t.transfer_id,
				t.budget_id,
				t.income_id,
				t.account_id,
				t.statement_id
			from transact t
			left join budget b on t.budget_id = b.id
			left join income i on t.income_id = i.id
			left join account a on t.account_id = a.id
			left join statement s on t.statement_id = s.id
			where 1 = 1
		"""
		params = []

		if start_date:
			sql_query += " and t.date >= ?"
			params.append(f'{start_date} 00:00:00')
		if end_date:
			sql_query += " and t.date < ?"
			params.append(f'{end_date} 00:00:00')
		if account_id is not None:
			sql_query += " and t.account_id = ?"
			params.append(account_id)
		if budget_id is not None:
			sql_query += " and t.budget_id = ?"
			params.append(budget_id)
		if income_id is not None:
			sql_query += " and t.income_id = ?"
			params.append(income_id)
		if statement_id is not None:
			sql_query += " and t.statement_id = ?"
			params.append(statement_id)
		if is_transfer is not None:
			sql_query += " and t.is_transfer = ?"
			params.append(int(is_transfer))
		if search:
			sql_query += " and lower(t.description) like ?"
			params.append(f'%{search.lower()}%')

		sql_query += " order by t.date desc, t.id desc;"

		return pd.read_sql_query(sql_query, self._conn, params=params)

	def get_monthly_income(self, start_date: str, end_date: str):
		"""Per-income credit totals for each month in [start_date, end_date).

		Income lives on transact rather than on the budget views, so this does not go through
		budget_transact: it is money arriving, before any distribution splits it up.
		"""
		sql_query = """
			select
				strftime('%Y-%m', t.date) as month,
				ifnull(i.name, 'unassigned') as name,
				sum(t.amount) as amount
			from transact t
			left join income i on t.income_id = i.id
			where t.debit_or_credit = '+'
				and t.is_transfer = 0
				and t.income_id is not null
				and t.date >= ?
				and t.date < ?
			group by month, i.id, i.name
			order by month, i.name;
		"""
		start = f'{start_date} 00:00:00'
		end = f'{end_date} 00:00:00'
		return pd.read_sql_query(sql_query, self._conn, params=[start, end])

	def update_budget(self, transact_id, budget_id):
		with write_lock:
			self._cursor.execute(
				"update transact set budget_id = ? where id = ?;",
				(budget_id, transact_id),
			)
			self._conn.commit()

	def update_income(self, transact_id, income_id):
		"""Updating income_id fires the update_transact_distribution trigger, which clones the
		income's primary distribution onto this transaction. That is intentional."""
		with write_lock:
			self._cursor.execute(
				"update transact set income_id = ? where id = ?;",
				(income_id, transact_id),
			)
			self._conn.commit()

	def update_description(self, transact_id, description):
		with write_lock:
			self._cursor.execute(
				"update transact set description = ? where id = ?;",
				(description, transact_id),
			)
			self._conn.commit()
