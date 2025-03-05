import sys
sys.path.append('./')

import pandas as pd
from database.dbio import sql
from logic.shared_logic import generate_accounts_df

def run_report(start_date='1900-01-01', end_date=''):
   if not end_date: 
      end_date = pd.to_datetime('now').strftime('%Y-%m-%d')
   else:
      start_date += '-01'
      end_date += '-01'

   staged_income = sql.get_staged_transactions_by_income()
   # report = sql.get_balance_update_report()
   budget_distribution = generate_accounts_df(False)
   budget_distribution = budget_distribution[budget_distribution['Category'] != 'income']

   income_id_map = {}
   for i, row in staged_income.iterrows():
      income_id_map[row['name']] = row['id']

   # print(staged_income)
   # print(report)

   cols = ['id', 'Name']+[i for i in budget_distribution.columns.tolist() if '%' in i]

   budget_distribution = budget_distribution[cols]

   if any(budget_distribution[cols[2:]].sum().round(2) != 1.00):
      print('Warning: Budget percentages do not add up to 1.0')
      print(budget_distribution[cols[2:]].sum().round(2) != 1.00)
      print()
      print(budget_distribution)
      print()
      print(budget_distribution[cols[2:]].sum().round(2))

   budget_distribution.rename(columns={'Name':'name'}, inplace=True)

   # merged_df = pd.merge(report, budget_distribution, how='outer', on='name').fillna(0)
   # print(budget_distribution)
   for i, row in budget_distribution.iterrows():
      # credit = 0
      name = row['name']
      if name == 'Leftover': continue

      if name == 'unassigned': 
         # row = merged_df[merged_df['name'] == 'Leftover'].iloc[0]
         pass
      else:
         for col in cols:
            # print(name, col, col[:-2])
            if col[:-2] not in staged_income['name'].tolist(): continue
            sql.update_distribution_weight(income_id_map[col[:-2]], row['id'], row[col])
   #          credit += row[col] * staged_income[staged_income['name'] == col[:-2]].iloc[0]['credit']

   #    report.loc[report['name'] == name,'total_credits'] = credit



   # report.loc[report['name'] == 'unassigned','total_credits'] += sum(staged_income['credit']) - sum(report['total_credits'])

   # report['new_balance'] = report['initial_balance'] + report['total_credits'] - report['total_debits']
   # report['initial_balance'] = report['initial_balance'].round(2)
   # report['total_debits'] = report['total_debits'].round(2)
   # report['total_credits'] = report['total_credits'].round(2)
   # report['new_balance'] = report['new_balance'].round(2)

   report = sql.get_budget_balance(start_date, end_date)
   report = report[[col for col in report.columns.tolist() if '_id' not in col]]

   print(report.sort_values('account').round(2).reset_index(drop=True))
   print(report.groupby('account').sum().round(2)[['total_debits', 'total_credits', 'balance']])
   print()
   print(report[['total_debits', 'total_credits', 'balance']].sum().round(2))
