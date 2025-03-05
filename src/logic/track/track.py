import sys
sys.path.append('./')

import pandas as pd
from inputs import inputs
from database.dbio import sql
from logic.parsers import parse

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