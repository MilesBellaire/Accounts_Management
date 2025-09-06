import sys
sys.path.append('./')

import pandas as pd
from database.io.dbio import sql
from prettytable import PrettyTable
from datetime import timedelta
import matplotlib.pyplot as plt

def run_report(start_date='1900-01-01', end_date=''):
   if not end_date: 
      end_date = (pd.to_datetime('now') + timedelta(days=1)).strftime('%Y-%m-%d')
   else:
      start_date += '-01'
      end_date += '-01'

   print(start_date, '-', end_date)


   # report = sql.get_balance_update_report()

   # report.loc[report['name'] == 'unassigned','total_credits'] += sum(staged_income['credit']) - sum(report['total_credits'])

   # report['new_balance'] = report['initial_balance'] + report['total_credits'] - report['total_debits']
   # report['initial_balance'] = report['initial_balance'].round(2)
   # report['total_debits'] = report['total_debits'].round(2)
   # report['total_credits'] = report['total_credits'].round(2)
   # report['new_balance'] = report['new_balance'].round(2)

   report = sql.budget_balance.get_asof(start_date, end_date)
   report = report[[col for col in report.columns.tolist() if '_id' not in col]]

   if report.empty: 
      print('No transactions found')
      return

   # print(report.sort_values('account').round(2).reset_index(drop=True))
   # print(report.groupby('account').sum().round(2)[['total_debits', 'total_credits', 'balance']])
   # print()
   # print(report[['total_debits', 'total_credits', 'balance']].sum().round(2))

   by_budget = report.sort_values('account').round(2).reset_index(drop=True)
   by_budget_table = PrettyTable()
   by_budget_table.align = 'r'
   by_budget_table.field_names = by_budget.columns
   by_budget_table.add_rows(by_budget.values.tolist())
   print(by_budget_table)

   report['account'].fillna('savings', inplace=True)
   by_account = report.groupby('account').sum().round(2)[['initial_balance', 'total_debits', 'total_credits', 'change', 'balance']]
   # print(by_account)
   by_account_table = PrettyTable()
   by_account_table.align = 'r'
   by_account_table.field_names = ['account'] + by_account.columns.tolist()
   formatted_rows = [
      [account] + [f"{value:.2f}" for value in by_account.loc[account]]
      for account in by_account.index
   ]
   by_account_table.add_rows(formatted_rows)
   print(by_account_table)

   total = report[['initial_balance', 'total_debits', 'total_credits', 'change', 'balance']].sum().round(2)
   total_table = PrettyTable()
   total_table.align = 'r'
   total_table.field_names = [''] + total.index.tolist()
   total_table.add_row(['Totals'] + total.tolist())
   print(total_table)

   if end_date != (pd.to_datetime('now') + timedelta(days=1)).strftime('%Y-%m-%d'): return
   
   df = sql.get_account_balance_diffs()

   table = PrettyTable()
   table.align = 'r'
   table.field_names = df.columns
   table.add_rows(df.round(2).values.tolist())
   print("\n\nAccount Balance vs Budget Balances\n")
   print(table)

   df_totals = df[['budget_balance', 'account_balance', 'diff']].sum().round(2)
   # df_totals = df_totals
   total_table = PrettyTable()
   total_table.align = 'r'
   total_table.field_names = [''] + df_totals.index.tolist()
   total_table.add_row(['Totals'] + df_totals.tolist())
   print(total_table)