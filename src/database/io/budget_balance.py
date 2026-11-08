import pandas as pd

from database.io.lock import write_lock


class budget_balance:
	def __init__(self, conn):
		self._conn = conn
		self._cursor = conn.cursor()

	def get_all(self):
		return pd.read_sql_query("select * from budget_balance;", self._conn)

	def get_asof(self, start_date: str, end_date: str):
		"""Per-budget balances over [start_date, end_date), both 'YYYY-MM-DD'.

		initial_budget is everything before the window; new_balance is the window itself.
		"""
		sql_query = """
			with initial_budget as (
				select
					a.name as account,
					ifnull(b.name, 'undecided') as name,
					sum(iif(bt.debit_or_credit = '+', ifnull(bt.amount, 0), ifnull(-bt.amount,0))) as balance,
					a.id as account_id,
					ifnull(b.id, 0) as budget_id
				from budget_transact bt
				left join budget b on bt.budget_id = b.id
				left join transact t on bt.transact_id = t.id
				left join account a on b.account_id = a.id
				where bt.date < ?
				group by a.name, b.name
			),
			new_balance as (
				select
					a.name as account,
					ifnull(b.name, 'undecided') as name,
					sum(iif(bt.debit_or_credit = '-' and bt.budget_balance_transfer_id is null, bt.amount, 0)) as total_debits,
					sum(iif(bt.debit_or_credit = '+' and bt.budget_balance_transfer_id is null, bt.amount, 0)) as total_credits,
					sum(iif(bt.budget_balance_transfer_id is not null, iif(bt.debit_or_credit = '+', ifnull(bt.amount, 0), ifnull(-bt.amount,0)), 0)) as total_transfered,
					sum(iif(bt.debit_or_credit = '+', bt.amount, -bt.amount)) as change,
					a.id as account_id,
					ifnull(b.id,0) as budget_id
				from budget_transact bt
				left join budget b on bt.budget_id = b.id
				left join transact t on bt.transact_id = t.id
				left join account a on b.account_id = a.id
				where bt.date >= ? and bt.date < ?
				group by a.name, b.name
			)
			select
				budget_balance.account,
				budget_balance.name,
				ifnull(initial_budget.balance,0.0) as initial_balance,
				ifnull(new_balance.total_debits,0.0) as debits,
				ifnull(new_balance.total_credits,0.0) as credits,
				ifnull(total_transfered, 0.0) as transfered,
				ifnull(new_balance.change,0.0) as change,
				ifnull(new_balance.change,0.0) + ifnull(initial_budget.balance,0) as balance,
				budget_balance.account_id,
				budget_balance.budget_id
			from budget_balance
			left join new_balance on budget_balance.budget_id = new_balance.budget_id
			left join initial_budget on budget_balance.budget_id = initial_budget.budget_id;
		"""
		start = f'{start_date} 00:00:00'
		end = f'{end_date} 00:00:00'
		return pd.read_sql_query(sql_query, self._conn, params=[start, start, end])

	def get_monthly(self, start_date: str, end_date: str):
		"""Per-budget totals for each month in [start_date, end_date), both 'YYYY-MM-DD'.

		The same figures get_asof reports for one window, grouped by month instead of
		collapsed - so debits still exclude transfers and transfers are reported on their own.
		"""
		sql_query = """
			select
				strftime('%Y-%m', bt.date) as month,
				a.name as account,
				ifnull(b.name, 'undecided') as name,
				sum(iif(bt.debit_or_credit = '-' and bt.budget_balance_transfer_id is null, bt.amount, 0)) as debits,
				sum(iif(bt.debit_or_credit = '+' and bt.budget_balance_transfer_id is null, bt.amount, 0)) as credits,
				sum(iif(bt.budget_balance_transfer_id is not null, iif(bt.debit_or_credit = '+', bt.amount, -bt.amount), 0)) as transfered,
				sum(iif(bt.debit_or_credit = '+', bt.amount, -bt.amount)) as change,
				ifnull(b.id, 0) as budget_id
			from budget_transact bt
			left join budget b on bt.budget_id = b.id
			left join account a on b.account_id = a.id
			where bt.date >= ? and bt.date < ?
			group by month, b.id, b.name, a.name
			order by month, b.name;
		"""
		start = f'{start_date} 00:00:00'
		end = f'{end_date} 00:00:00'
		return pd.read_sql_query(sql_query, self._conn, params=[start, end])

	def get(self, name):
		row = self._cursor.execute(
			"select balance from budget_balance where name = ?;", (name,)
		).fetchone()
		return row[0] if row else None

	def get_transfers(self):
		sql_query = """
			select
				t.id,
				t.date,
				t.amount,
				f.name as from_budget,
				d.name as to_budget
			from budget_balance_transfer t
			left join budget f on t.from_budget_id = f.id
			left join budget d on t.to_budget_id = d.id
			order by t.date desc, t.id desc;
		"""
		return pd.read_sql_query(sql_query, self._conn)

	def insert_transfer(self, from_budget_id, to_budget_id, amount):
		sql_query = """
			insert into budget_balance_transfer (from_budget_id, to_budget_id, amount, date)
			values (?, ?, ?, datetime('now'));
		"""
		with write_lock:
			self._cursor.execute(sql_query, (from_budget_id, to_budget_id, amount))
			self._conn.commit()

		return self._cursor.lastrowid

	def delete_transfer(self, transfer_id):
		with write_lock:
			self._cursor.execute(
				"delete from budget_balance_transfer where id = ?;", (transfer_id,)
			)
			self._conn.commit()
