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

def run_report():
   staged_income = sql.get_staged_transactions_by_income()
   report = sql.get_balance_update_report()
   budget_distribution = generate_accounts_df(False)
   budget_distribution = budget_distribution[budget_distribution['Category'] != 'income']

   print(staged_income)
   # print(report)

   cols = ['Name']+[i for i in budget_distribution.columns.tolist() if '%' in i]

   budget_distribution = budget_distribution[cols]

   # print(sum(budget_distribution['salary %']))

   budget_distribution.rename(columns={'Name':'name'}, inplace=True)
   total_credits = []

   # print(pd.merge(report, budget_distribution, how='outer', on='name'))
   for i, row in pd.merge(report, budget_distribution, how='outer', on='name').iterrows():
      credit = 0
      if row['name'] == 'Leftover': continue

      if row['name'] == 'undecided': 
         credit = 0
      else:
         for col in cols:
            col = col
            if col[:-2] not in staged_income['name'].tolist(): continue
            credit += row[col] * staged_income[staged_income['name'] == col[:-2]].iloc[0]['credit']

      total_credits += [credit]



   report['total_credits'] = total_credits
   report.loc[report['name'] == 'undecided','total_credits'] = sum(staged_income['credit']) - sum(total_credits)

   report['new_balance'] = report['initial_balance'] + report['total_credits'] - report['total_debits']
   print(report)
   print(report.groupby('account').sum()[['initial_balance', 'total_debits', 'total_credits', 'new_balance']])

   print('total balance:', sum(report['new_balance']))
   # exit()