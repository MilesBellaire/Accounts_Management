import pandas as pd

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
      return pd.read_sql_query(sql_query, self._conn)


   def get_units(self):
      sql_query = f"""
         select * from budget_unit;
      """
      return pd.read_sql_query(sql_query, self._conn)


   def insert(self, name, equation, tags, tracking_type_id, unit_id, value, cap, account_id):
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
      self._cursor.execute(sql_query)
      self._conn.commit()

      return self._cursor.lastrowid


   def update(self, budget_id, name, equation, tags, tracking_type_id, unit_id, value, cap, account_id):
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
      self._cursor.execute(sql_query)
      self._conn.commit()

   def delete(self, budget_id):
      delete_budget = f"delete from budget where id = {budget_id};"
      delete_distribution_budget = f"delete from distribution_budget where budget_id = {budget_id};"
      update_transact = f"update transact set budget_id = -1 where budget_id = {budget_id};"
      
      self._cursor.execute(delete_budget)
      self._cursor.execute(delete_distribution_budget)
      self._cursor.execute(update_transact)
      self._conn.commit()