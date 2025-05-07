import pandas as pd

class statement:
   def __init__(self, conn):
      self._conn = conn
      self._cursor = conn.cursor()

   def insert(self, filename, startdate, enddate) -> int:
      sql_query = """
         insert into statement(name, start_date, end_date) 
         values (?, ?, ?);
      """
      self._cursor.execute(sql_query,(filename, startdate.strftime('%Y-%m-%d %H:%M:%S'), enddate.strftime('%Y-%m-%d %H:%M:%S')))

      self._conn.commit()

      return self._cursor.lastrowid

   def delete(self, id):
      sql_query = "update transact set transfer_id = null where transfer_id in (select id from transact where statement_id = ?);"
      self._cursor.execute(sql_query,(id,))

      sql_query = "delete from statement where id = ?;"
      self._cursor.execute(sql_query,(id,))

      sql_query = "delete from transact where statement_id = ?;"
      self._cursor.execute(sql_query,(id,))

      sql_query = """delete from distribution_budget 
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
      self._cursor.execute(sql_query,(id,))

      sql_query = """
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
      self._cursor.execute(sql_query,(id,))

      self._conn.commit()

   def exists(self, filename):
      sql_query = "select count(*) from statement where name = ?;"
      return self._cursor.execute(sql_query,(filename,)).fetchone()[0]

   def get_id(self, filename):
      sql_query = "select id from statement where name = ?;"
      return self._cursor.execute(sql_query,(filename,)).fetchone()[0]
   

   def get_account_id(self, account) -> int:
      sql_query = f"select id from account where number = '{account}';"
      df = pd.read_sql_query(sql_query, self._conn)

      return int(df.values[0][0]) if len(df) > 0 else -1

   def stage_transactions(self, transactions: pd.DataFrame):
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
               abs(strftime('%d', t1.date) - strftime('%d', t2.date)) <= 2
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
         self._cursor.execute(sql_insert_query, [
            row.Date,
            row.Description,
            row.DebitOrCredit,
            row.Amount,
            self.get_account_id(row.Account),
            row.Category,
            int(row.AssociatedId) if row.AssociatedId != '' else '',
            row.IsTransfer,
            row.StatementId
         ])
         self._cursor.execute(sql_update_query)

      self._conn.commit()

