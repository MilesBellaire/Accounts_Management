import pandas as pd

from database.io.lock import write_lock
from database.io.util import nullable


def _as_id(value):
	"""Category ids arrive from pandas as floats or blanks; store them as ints or NULL."""
	value = nullable(value)
	return None if value is None else int(value)


class statement:
	def __init__(self, conn):
		self._conn = conn
		self._cursor = conn.cursor()

	def get_all(self):
		sql_query = """
			select
				s.id,
				s.name,
				s.start_date,
				s.end_date,
				count(t.id) as transactions,
				sum(iif(t.debit_or_credit = '-', t.amount, 0)) as debits,
				sum(iif(t.debit_or_credit = '+', t.amount, 0)) as credits
			from statement s
			left join transact t on t.statement_id = s.id
			group by s.id, s.name, s.start_date, s.end_date
			order by s.start_date desc;
		"""
		return pd.read_sql_query(sql_query, self._conn)

	def insert(self, filename, startdate, enddate) -> int:
		sql_query = """
			insert into statement(name, start_date, end_date)
			values (?, ?, ?);
		"""
		with write_lock:
			self._cursor.execute(
				sql_query,
				(
					filename,
					startdate.strftime('%Y-%m-%d %H:%M:%S'),
					enddate.strftime('%Y-%m-%d %H:%M:%S'),
				),
			)
			self._conn.commit()

		return self._cursor.lastrowid

	def delete(self, id):
		clear_transfer_links = """
			update transact set transfer_id = null
			where transfer_id in (select id from transact where statement_id = ?);
		"""
		# Distributions cloned by the transact triggers are only removed when this statement is
		# the sole statement referencing them.
		delete_distribution_budgets = """
			delete from distribution_budget
			where distribution_id in (
				select d.id
				from distribution d
				join transact t on d.id = t.distribution_id
				group by d.id
				having count(distinct t.statement_id) = 1
			) and distribution_id in (
				select d.id
				from distribution d
				join transact t on d.id = t.distribution_id
				where t.statement_id = ?
			);
		"""
		delete_distributions = """
			delete from distribution
			where id in (
				select d.id
				from distribution d
				join transact t on d.id = t.distribution_id
				group by d.id
				having count(distinct t.statement_id) = 1
			) and id in (
				select d.id
				from distribution d
				join transact t on d.id = t.distribution_id
				where t.statement_id = ?
			);
		"""

		with write_lock:
			self._cursor.execute(clear_transfer_links, (id,))
			self._cursor.execute("delete from statement where id = ?;", (id,))
			self._cursor.execute("delete from transact where statement_id = ?;", (id,))
			self._cursor.execute(delete_distribution_budgets, (id,))
			self._cursor.execute(delete_distributions, (id,))
			self._conn.commit()

	def exists(self, filename):
		return self._cursor.execute(
			"select count(*) from statement where name = ?;", (filename,)
		).fetchone()[0]

	def get_id(self, filename):
		row = self._cursor.execute(
			"select id from statement where name = ?;", (filename,)
		).fetchone()
		return row[0] if row else None

	def get_account_id(self, account) -> int:
		row = self._cursor.execute(
			"select id from account where number = ?;", (str(account),)
		).fetchone()
		return int(row[0]) if row else -1

	def stage_transactions(self, transactions: pd.DataFrame):
		transactions = transactions.copy()
		transactions['Date'] = pd.to_datetime(transactions['Date']).dt.strftime('%Y-%m-%d %H:%M:%S')

		# Pair each transfer with its opposite leg in the other account.
		link_transfers = """
			UPDATE transact as t1
			SET transfer_id = (
				SELECT t2.id
				FROM transact AS t2
				WHERE t1.amount = t2.amount
				AND t2.is_transfer = 1
				AND (
					strftime('%Y', t1.date) = strftime('%Y', t2.date) and
					strftime('%m', t1.date) = strftime('%m', t2.date) and
					abs(strftime('%d', t1.date) - strftime('%d', t2.date)) <= 2
				)
				AND t1.debit_or_credit <> t2.debit_or_credit
				AND t2.transfer_id IS NULL or t2.transfer_id = t1.id
				limit 1
			)
			WHERE transfer_id IS NULL and is_transfer = 1;
		"""

		with write_lock:
			for row in transactions.itertuples(index=False):
				category_column = 'budget_id' if row.DebitOrCredit == '-' else 'income_id'
				insert_transaction = f"""
					insert into transact(
							date,
							insert_date,
							description,
							debit_or_credit,
							amount,
							account_id,
							class,
							{category_column},
							is_transfer,
							statement_id
						)
					select ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?;
				"""
				self._cursor.execute(
					insert_transaction,
					(
						row.Date,
						row.Description,
						row.DebitOrCredit,
						nullable(row.Amount),
						self.get_account_id(row.Account),
						row.Category,
						_as_id(row.AssociatedId),
						nullable(row.IsTransfer),
						nullable(row.StatementId),
					),
				)
				self._cursor.execute(link_transfers)

			self._conn.commit()
