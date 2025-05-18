import sqlite3
import pandas as pd
from database.io.budget import budget
from database.io.income import income
from database.io.statement import statement
from database.io.budget_balance import budget_balance

class sql:
	_conn = sqlite3.connect('./database/db.db')
	_cursor = _conn.cursor()

	budget = budget(_conn)
	income = income(_conn)
	statement = statement(_conn)
	budget_balance = budget_balance(_conn)

	def close():
		sql._conn.close()
	
	def get_keyword(budget_id=None, income_id=None):
		sql_query = f"""
			select 
				k.id,
				k.text,
				k.budget_id,
				k.income_id
			from keyword k
		"""

		if budget_id: sql_query += f"where k.budget_id = {budget_id}"
		elif income_id: sql_query += f"where k.income_id = {income_id}"
		
		df = pd.read_sql_query(sql_query, sql._conn)
		return df
	
	def insert_keyword(text, budget_id=None, income_id=None):
		sql._cursor.execute(
			"insert into keyword values (?, ?, ?);",
			(text, budget_id, income_id),
		)

		sql._conn.commit()

		return sql._cursor.lastrowid
	
	def delete_keyword(id):
		sql._cursor.execute(
			"delete from keyword where id = ?;",
			(id,),
		)

		sql._conn.commit()
	
	def get_constants():
		sql_query = "select * from constants;"
		return pd.read_sql_query(sql_query, sql._conn)
	
	# Not used
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
	
	def get_transactions_by_income():
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

		sql._conn.commit()

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

	def insert_distribution_budget(income_id, budget_id):
		sql_query = f"""
			insert into distribution_budget(distribution_id, budget_id, weight)
			select primary_distribution_id, {budget_id}, 0
			from income where id = {income_id};
		"""
		sql._cursor.execute(sql_query)
		sql._conn.commit()

		return sql._cursor.lastrowid
	
	# Not used
	def delete_distribution_budget(income_id, budget_id):
		sql_query = f"""
			delete from distribution_budget
			where distribution_id = (select primary_distribution_id from income where id = {income_id})
				and budget_id = {budget_id};
		"""
		sql._cursor.execute(sql_query)
		sql._conn.commit()

	def get_transact_amount_by_income(income_id):
		sql_query = f"""
			select sum(amount) from transact
			where distribution_id in (
				select id
				from distribution
				where income_id = {income_id}
			);
		"""
		return pd.read_sql_query(sql_query, sql._conn)
	
	def get_transact_amount_by_budget(budget_id):
		sql_query = f"""
			select sum(amount) from transact
			where distribution_id in (
				select id
				from distribution
				where budget_id = {budget_id}
			);
		"""
		return pd.read_sql_query(sql_query, sql._conn)
	
	def get_account_balance_diffs():
		sql_query = f"""
			select * from account_sys_diff;
		"""
		return pd.read_sql_query(sql_query, sql._conn)