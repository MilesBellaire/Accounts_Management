import pandas as pd

class budget_balance:
   def __init__(self, conn):
      self._conn = conn
      self._cursor = conn.cursor()

   def get_all(self):
      sql_query = f"""
         select * from budget_balance;
      """
      return pd.read_sql_query(sql_query, self._conn)

   # date should be in the form of "YYYY-MM-DD"
   def get_asof(self, start_date: str, end_date: str):
      start = start_date.split('-')
      end = end_date.split('-')
      sql_query = f"""
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
            where bt.date < '{start[0]}-{start[1]}-{start[2]} 00:00:00'
            group by a.name, b.name
         ),
         new_balance as (
            select 
               a.name as account,
               ifnull(b.name, 'undecided') as name,
               -- ifnull(ib.balance,0.0) as initial_balance,
               sum(iif(bt.debit_or_credit = '+', 0, bt.amount)) as total_debits,
               sum(iif(bt.debit_or_credit = '+', bt.amount, 0)) as total_credits,
               sum(iif(bt.debit_or_credit = '+', bt.amount, -bt.amount)) as change,
               -- sum(iif(bt.debit_or_credit = '+', bt.amount, -bt.amount)) + ifnull(ib.balance,0) as balance,
               a.id as account_id,
               ifnull(b.id,0) as budget_id
            from budget_transact bt
            left join budget b on bt.budget_id = b.id
            left join transact t on bt.transact_id = t.id
            left join account a on b.account_id = a.id
            -- left join initial_budget ib on ifnull(b.name, 'undecided') = ib.name
            where bt.date >= '{start[0]}-{start[1]}-{start[2]} 00:00:00' and bt.date < '{end[0]}-{end[1]}-{end[2]} 00:00:00'
            group by a.name, b.name--, ib.balance
         )
         -- select * from new_balance;
         select 
            budget_balance.account,
            budget_balance.name,
            ifnull(initial_budget.balance,0.0) as initial_balance,
            ifnull(new_balance.total_debits,0.0) as total_debits,
            ifnull(new_balance.total_credits,0.0) as total_credits,
            ifnull(new_balance.change,0.0) as change,
            ifnull(new_balance.change,0.0) + ifnull(initial_budget.balance,0) as balance,
            budget_balance.account_id,
            budget_balance.budget_id
         from budget_balance
         left join new_balance on budget_balance.budget_id = new_balance.budget_id
         left join initial_budget on budget_balance.budget_id = initial_budget.budget_id;
      """
      return pd.read_sql_query(sql_query, self._conn)

   def get(self, name):
      sql_query = f"""
         select balance from budget_balance where name = ?;
      """
      return self._cursor.execute(sql_query,(name,)).fetchone()[0]

   def insert_transfer(self, from_budget_id, to_budget_id, amount):
      sql_query = f"""
         insert into budget_balance_transfer (from_budget_id, to_budget_id, amount, date)
         values (?, ?, ?, datetime('now'));
      """
      self._cursor.execute(sql_query,(from_budget_id, to_budget_id, amount))
      self._conn.commit()

      return self._cursor.lastrowid