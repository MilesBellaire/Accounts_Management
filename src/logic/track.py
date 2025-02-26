import sys
sys.path.append('./')

import pandas as pd
from inputs import inputs
from database.dbio import sql
from logic.parsers import parse
from logic.shared_logic import generate_accounts_df

def track(file_name):
   transactions = parse(file_name)

   credits = transactions.loc[transactions['DebitOrCredit'] == '+']
   debits = transactions.loc[transactions['DebitOrCredit'] == '-']
   # print(count)
   budgets = sql.get_budget()
   incomes = sql.get_income()

   for i, row in debits.iterrows():
      if row['IsTransfer'] == 1: continue

      if row['CheckingOrSavings'] == 'c':
         keyword_matches = sql.get_budget_id_by_keyword(row['Description'])
         # print(len(keyword_matches))

         # If multiple keywords match
         if len(keyword_matches) > 1:
            cat_input = inputs.get_options(list(keyword_matches['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")
            debits.loc[i, 'Category'] = cat_input
            debits.loc[i, 'AssociatedId'] = keyword_matches.loc[keyword_matches['name'] == cat_input, 'id'].iloc[0]
         # If one keyword matches
         elif len(keyword_matches) == 1:
            debits.loc[i, 'Category'] = keyword_matches['name'].iloc[0]
            debits.loc[i, 'AssociatedId'] = keyword_matches['id'].iloc[0]
         # If no keywords match
         else:
            categories = budgets.loc[budgets['tracking_type'] == 'keyword', ['id','name']]
            categories = pd.concat([categories, pd.DataFrame({'name': ['Unknown'], 'id': [-1]})], ignore_index=True)

            cat_input = inputs.get_options(list(categories['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")
            cat_id = int(categories.loc[categories['name'] == cat_input, 'id'].iloc[0])

            debits.loc[i, 'Category'] = cat_input
            debits.loc[i, 'AssociatedId'] = cat_id

            if cat_id == -1:
               continue

            val = ''
            while val != 'e':
               val = inputs.get_str("Enter new keyword for category(e to end): ")
               if val != 'e':
                  sql.insert_keyword(val, budget_id=cat_id)
                  
      elif row['CheckingOrSavings'] == 's':
         categories = budgets.loc[budgets['tracking_type'] == 'withdrawal', ['id','name']]
         cat_input = inputs.get_options(list(categories['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")

         debits.loc[i, 'Category'] = cat_input
         debits.loc[i, 'AssociatedId'] = categories.loc[categories['name'] == cat_input, 'id'].iloc[0]


   for i, row in credits.iterrows():
      if row['IsTransfer'] == 1: continue

      keyword_matches = sql.get_income_id_by_keyword(row['Description'])
      # print(len(keyword_matches))
      # If multiple keywords match
      if len(keyword_matches) > 1:
         cat_input = inputs.get_options(list(keyword_matches['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")
         credits.loc[i, 'Category'] = cat_input
         credits.loc[i, 'AssociatedId'] = keyword_matches.loc[keyword_matches['name'] == cat_input, 'id'].iloc[0]
      # If one keyword matches
      elif len(keyword_matches) == 1:
         credits.loc[i, 'Category'] = keyword_matches['name'].iloc[0]
         credits.loc[i, 'AssociatedId'] = keyword_matches['id'].iloc[0]
      # If no keywords match
      else:
         categories = incomes.loc[(incomes['tracking_type'] == 'keyword') | (incomes['tracking_type'] == 'withdrawal'), ['id','name']]
         categories = pd.concat([categories, pd.DataFrame({'name': ['Unknown'], 'id': [-1]})], ignore_index=True)

         cat_input = inputs.get_options(list(categories['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")
         cat_id = int(categories.loc[categories['name'] == cat_input, 'id'].iloc[0])

         credits.loc[i, 'Category'] = cat_input
         credits.loc[i, 'AssociatedId'] = cat_id

         if cat_id == -1: continue

         val = ''
         while val != 'e':
            val = inputs.get_str("Enter new keyword for category(e to end): ")
            if val != 'e':
               sql.insert_keyword(val, budget_id=cat_id)

   print(credits)
   print(debits)

   transactions = pd.concat([debits, credits], ignore_index=True)

   sql.stage_transactions(transactions)

   # sql.close()

def run_report(asof_date=None):
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

   report = sql.get_budget_balance()
   report = report[[col for col in report.columns.tolist() if '_id' not in col]]

   print(report.sort_values('account').round(2).reset_index(drop=True))
   print(report.groupby('account').sum().round(2)[['total_debits', 'total_credits', 'balance']])
   print()
   print(report[['total_debits', 'total_credits', 'balance']].sum().round(2))
