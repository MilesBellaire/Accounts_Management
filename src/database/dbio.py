import sqlite3
import pandas as pd

class sql:
	_conn = sqlite3.connect('./database/db.db')
	_cursor = _conn.cursor()

	def commit():
		sql._conn.commit()

	def close():
		sql._conn.close()

	def get_income():
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
			join unit u on i.unit_id = u.id
			left join distribution d on i.primary_distribution_id = d.id
			left join distribution_budget db on d.id = db.distribution_id
			left join budget b on db.budget_id = b.id
			group by i.id, i.name, i.value, u.abv, i.equation, i.tags, t.name
		"""
		df = pd.read_sql_query(sql_query, sql._conn)
		
		return df

	def get_budget():
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
			join unit u on b.unit_id = u.id
			join account a on b.account_id = a.id
		"""

		return pd.read_sql_query(sql_query, sql._conn)
	
	def get_keyword(budget_id=None, income_id=None):
		sql_query = f"""
			select 
				k.text,
				k.budget_id,
				k.income_id
			from keyword k
			"""

		if budget_id: sql_query += f"where k.budget_id = {budget_id}"
		elif income_id: sql_query += f"where k.income_id = {income_id}"
		
		df = pd.read_sql_query(sql_query, sql._conn)
		return df
	
	def get_budget_id_by_keyword(text):
		text = text.replace('\'', '\'\'')
		sql_query = f"""
			select 
				GROUP_CONCAT(k.text, ', ') as text,
				k.budget_id as id,
				b.name
			from keyword k
			join budget b on k.budget_id = b.id
			where '{text}' like '%'||k.text||'%' 
			group by k.budget_id, b.name
		"""
		return pd.read_sql_query(sql_query, sql._conn)
	
	def get_income_id_by_keyword(text):
		text = text.replace('\'', '\'\'')
		sql_query = f"""
			select 
				GROUP_CONCAT(k.text, ', ') as text,
				k.income_id as id,
				i.name
			from keyword k
			join income i on k.income_id = i.id
			where '{text}' like '%'||k.text||'%' 
			group by k.income_id, i.name
		"""
		return pd.read_sql_query(sql_query, sql._conn)
	
	def insert_keyword(text, budget_id=None, income_id=None):
		sql._cursor.execute(
			"insert into keyword values (?, ?, ?);",
			(text, budget_id, income_id),
		)

		sql.commit()

	def get_account_id(account) -> int:
		sql_query = f"select id from account where number = '{account}';"
		df = pd.read_sql_query(sql_query, sql._conn)

		return int(df.values[0][0]) if len(df) > 0 else -1
	
	def stage_transactions(transactions: pd.DataFrame):
		transactions['Date'] = transactions['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')

		# update transfer_id
		sql_update_query = """
			UPDATE transact as t1
			SET transfer_id = (
				SELECT t2.id
				FROM transact AS t2
				WHERE t1.amount = t2.amount
				AND t2.is_transfer = 1
				AND (
					strftime('%Y', t1.date) = strftime('%Y', t2.date) and
					strftime('%m', t1.date) = strftime('%m', t2.date) and 
					abs(strftime('%d', t1.date) - strftime('%d', t2.date)) <= 1
				)
				AND t1.debit_or_credit <> t2.debit_or_credit
				AND t2.transfer_id IS NULL or t2.transfer_id = t1.id
				limit 1
			)
			WHERE transfer_id IS NULL and is_transfer = 1;
		"""

		for row in transactions.itertuples(index=False):
			sql_insert_query = f"""
				insert into transact(
						Date,
						insert_date,
						Description,
						debit_or_credit,
						amount,
						account_id,
						class,
						{'budget_id' if row.DebitOrCredit == '-' else 'income_id'},
						is_transfer,
						statement_id
					)
				select ?,datetime('now'),?,?,?,?,?,?,?,?;
			"""
			sql._cursor.execute(sql_insert_query, [
				row.Date,
				row.Description,
				row.DebitOrCredit,
				row.Amount,
				sql.get_account_id(row.Account),
				row.Category,
				int(row.AssociatedId) if row.AssociatedId != '' else '',
				row.IsTransfer,
				row.StatementId
			])
			sql._cursor.execute(sql_update_query)

		sql.commit()

	def get_constants():
		sql_query = "select * from constants;"
		return pd.read_sql_query(sql_query, sql._conn)
	
	def insert_statement(filename, startdate, enddate) -> int:
		sql_query = """
			insert into statement(name, start_date, end_date) 
			values (?, ?, ?);
		"""
		sql._cursor.execute(sql_query,(filename, startdate.strftime('%Y-%m-%d %H:%M:%S'), enddate.strftime('%Y-%m-%d %H:%M:%S')))

		sql.commit()

		return sql._cursor.lastrowid
	
	def delete_statement(id):
		sql_query = "update transact set transfer_id = null where transfer_id in (select id from transact where statement_id = ?);"
		sql._cursor.execute(sql_query,(id,))

		sql_query = "delete from statement where id = ?;"
		sql._cursor.execute(sql_query,(id,))

		sql_query = "delete from transact where statement_id = ?;"
		sql._cursor.execute(sql_query,(id,))

		sql.commit()

	def statement_exists(filename):
		sql_query = "select count(*) from statement where name = ?;"
		return sql._cursor.execute(sql_query,(filename,)).fetchone()[0]
	
	def get_statement_id(filename):
		sql_query = "select id from statement where name = ?;"
		return sql._cursor.execute(sql_query,(filename,)).fetchone()[0]
	
	def validate_staged_transactions(asof_date):
		sql_query = f"""
			select *
			from transact
			where date < (
				select ifnull(min(date), datetime('now')) from transact
				where (
					is_transfer = 1 and transfer_id is null
				) or (
					is_transfer = 0 and -1 in (budget_id, income_id)
				)
			);
		"""
		return pd.read_sql_query(sql_query, sql._conn)
	
	def get_staged_transactions_by_income():
		sql_query = f"""
			select i.id, i.name, sum(amount) as credit
			from transact t
			join income i on t.income_id = i.id
			where is_transfer = 0
			group by i.id, i.name;
		"""
		return pd.read_sql_query(sql_query, sql._conn)
		
	def update_distribution_weight(income_id, budget_id, weight):
		sql_query = f"""
			update distribution_budget
			set weight = ? 
			where distribution_id = (select primary_distribution_id from income where id = ?) 
				and budget_id = ?;
		"""
		sql._cursor.execute(sql_query,(weight,income_id,budget_id))

		sql.commit()
	
	def get_budget_balance():
		sql_query = f"""
			select * from budget_balance;
		"""
		return pd.read_sql_query(sql_query, sql._conn)