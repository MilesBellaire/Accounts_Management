import pandas as pd

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
      df = pd.read_sql_query(sql_query, self._conn)
      
      return df


   def get_id_by_keyword(self, text):
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
      return pd.read_sql_query(sql_query, self._conn)


   def get_units(self):
      sql_query = f"""
         select * from income_unit;
      """
      return pd.read_sql_query(sql_query, self._conn)
      
   def insert(self, name, equation, tags, tracking_type_id, unit_id, value, budget_ids):
      create_income = f"""
         insert into income(name, equation, tags, tracking_type_id, unit_id, value)
         values (
            '{name}', 
            {'\''+equation+'\'' if equation else 'null'}, 
            '{tags}', 
            {tracking_type_id}, 
            {unit_id if unit_id else 'null'}, 
            {value}
         );
      """
      self._cursor.execute(create_income)
      new_income_id = self._cursor.lastrowid

      create_distribution = f"""
         insert into distribution(name, income_id)
         select 'primary', i.id
         from income i
         where i.id = {new_income_id};
      """
      self._cursor.execute(create_distribution)
      new_id = self._cursor.lastrowid

      update_income_with_distribution = f"""
         update income
         set primary_distribution_id = {new_id}
         where id = {new_income_id};
      """
      self._cursor.execute(update_income_with_distribution)

      for id in budget_ids:
         create_distribution_budget = f"""
            insert into distribution_budget(distribution_id, budget_id, weight)
            select {new_id}, {id}, 0
            from budget
            where id = {id};
         """
         self._cursor.execute(create_distribution_budget)
      self._conn.commit()

      return self._cursor.lastrowid

   def update(self, income_id, name, equation, tags, tracking_type_id, unit_id, value):
      sql_query = f"""
         update income
         set name = '{name}', 
            equation = {'\''+equation+'\'' if equation else 'null'}, 
            tags = '{tags}', 
            tracking_type_id = {tracking_type_id}, 
            unit_id = {unit_id}, 
            value = {value}
         where id = {income_id};
      """
      self._cursor.execute(sql_query)
      self._conn.commit()

   def delete(self, income_id):
      delete_income = f"delete from income where id = {income_id};"
      delete_distribution_budget = f"""
         delete from distribution_budget
         where distribution_id in (
            select id
            from distribution
            where income_id = {income_id}
         );
      """
      delete_distribution = f"delete from distribution where income_id = {income_id};"
      update_transact = f"update transact set income_id = -1 where income_id = {income_id};"

      self._cursor.execute(delete_income)
      self._cursor.execute(delete_distribution_budget)
      self._cursor.execute(delete_distribution)
      self._cursor.execute(update_transact)
      self._conn.commit()
