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

		return sql._cursor.lastrowid

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
	
	# date should be in the form of "YYYY-MM-DD"
	def get_budget_balance(start_date: str, end_date: str):
		start = start_date.split('-')
		end = end_date.split('-')
		sql_query = f"""
			select 
				a.name as account,
				ifnull(b.name, 'undecided') as name,
				sum(iif(bt.debit_or_credit = '+', 0, bt.amount)) as total_debits,
				sum(iif(bt.debit_or_credit = '+', bt.amount, 0)) as total_credits,
				sum(iif(bt.debit_or_credit = '+', bt.amount, -bt.amount)) as balance,
				a.id as account_id,
				b.id as budget_id
			from budget_transact bt
			left join budget b on bt.budget_id = b.id
			left join transact t on bt.transact_id = t.id
			left join account a on b.account_id = a.id
			where bt.date >= '{start[0]}-{start[1]}-{start[2]} 00:00:00' and bt.date < '{end[0]}-{end[1]}-{end[2]} 00:00:00'
			group by a.name, b.name
		"""
		return pd.read_sql_query(sql_query, sql._conn)
	
	def insert_budget_balance_transfer(from_budget_id, to_budget_id, amount):
		sql_query = f"""
			insert into budget_balance_transfer (from_budget_id, to_budget_id, amount, date)
			values (?, ?, ?, datetime('now'));
		"""
		sql._cursor.execute(sql_query,(from_budget_id, to_budget_id, amount))
		sql.commit()

		return sql._cursor.lastrowid

	# Currently not used
	def finalize_budget_balance():

		# clone distributions and update transact with new distribution_ids
		sql_query = f"""
			insert into distribution(name, income_id, original_id)
			select distinct (datetime('now') || ' ' || d.id || ' ' || d.name || ' clone'), d.income_id, d.id
			from distribution d
			join income i on d.id = i.primary_distribution_id
			join transact t on i.id = t.income_id
			where t.distribution_id is null;

			update transact
			set distribution_id = (
				select d2.id
				from transact t
				join income i on t.income_id = i.id
				join distribution d1 on i.id = d1.income_id
				join distribution d2 on d1.id = d2.original_id
				where transact.id = t.id
				order by d2.id desc
				limit 1
			)
			where distribution_id is null;

			insert into distribution_budget(distribution_id, weight, budget_id)
			select distinct d.id, db.weight, db.budget_id
			from transact t
			join distribution d on t.distribution_id = d.id
			join distribution od on d.original_id = od.id
			join distribution_budget db on od.id = db.distribution_id;
		"""
		sql._cursor.execute(sql_query)
		sql.commit()

	def get_units():
		sql_query = f"""
			select * from unit;
		"""
		return pd.read_sql_query(sql_query, sql._conn)
	
	def insert_budget(name, equation, tags, tracking_type_id, unit_id, value, cap, account_id):
		print(name, equation, tags, tracking_type_id, unit_id, value, cap, account_id)
		sql_query = f"""
			insert into budget(name, equation, tags, tracking_type_id, unit_id, value, cap, account_id)
			values (
				'{name}', 
				{'\''+equation+'\'' if equation else 'null'}, 
				'{tags}', 
				{tracking_type_id}, 
				{unit_id if unit_id else 'null'}, 
				{value}, 
				{cap if cap else 'null'}, 
				{account_id}
			);
		"""
		sql._cursor.execute(sql_query)
		sql.commit()

		return sql._cursor.lastrowid

	def get_tracking_types():
		sql_query = f"""
			select * from tracking_type;
		"""
		return pd.read_sql_query(sql_query, sql._conn)
	
	def get_accounts():
		sql_query = f"""
			select * from account;
		"""
		return pd.read_sql_query(sql_query, sql._conn)
	
	def update_budget(budget_id, name, equation, tags, tracking_type_id, unit_id, value, cap, account_id):
		print(name, equation, tags, tracking_type_id, unit_id, value, cap, account_id)
		sql_query = f"""
			update budget
			set name = '{name}', 
				equation = {'\''+equation+'\'' if equation else 'null'}, 
				tags = '{tags}', 
				tracking_type_id = {tracking_type_id}, 
				unit_id = {unit_id}, 
				value = {value}, 
				cap = {cap if cap else 'null'}, 
				account_id = {account_id}
			where id = {budget_id};
		"""
		sql._cursor.execute(sql_query)
		sql.commit()

	def delete_budget(budget_id):
		sql_query = f"""
			delete from budget where id = {budget_id};
		"""
		sql._cursor.execute(sql_query)
		sql.commit()

	def insert_distribution_budget(income_id, budget_id):
		sql_query = f"""
			insert into distribution_budget(distribution_id, budget_id, weight)
			select primary_distribution_id, {budget_id}, 0
			from income where id = {income_id};
		"""
		sql._cursor.execute(sql_query)
		sql.commit()

		return sql._cursor.lastrowid