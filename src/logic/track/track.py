import sys
sys.path.append('./')

import pandas as pd
from inputs import inputs
from database.io.dbio import sql
from logic.parsers import parse
from logic.track.update_budget_distribution_weights import update_budget_distribution_weights

def track(file_name):

   if not update_budget_distribution_weights(): return

   transactions = parse(file_name)

   credits = transactions.loc[transactions['DebitOrCredit'] == '+']
   debits = transactions.loc[transactions['DebitOrCredit'] == '-']
   # print(count)
   budgets = sql.budget.get()
   incomes = sql.income.get()

   for i, row in debits.iterrows():
         if row['IsTransfer'] == 1: continue

      # if row['CheckingOrSavings'] == 'c':
         keyword_matches = sql.budget.get_id_by_keyword(row['Description'])
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
            categories = budgets[['id','name']]
            categories = pd.concat([categories, pd.DataFrame({'name': ['Unknown'], 'id': [-1]})], ignore_index=True)

            cat_input = inputs.get_options(list(categories['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")
            cat_id = int(categories.loc[categories['name'] == cat_input, 'id'].iloc[0])

            debits.loc[i, 'Category'] = cat_input
            debits.loc[i, 'AssociatedId'] = cat_id

            if cat_id in budgets.loc[budgets['tracking_type'] == 'keyword', ['id']].values:
               val = 'not blank'
               while val:
                  val = inputs.get_str("Enter new keyword for category(enter to end): ")
                  if val:
                     sql.insert_keyword(val, budget_id=cat_id)
                  
      # elif row['CheckingOrSavings'] == 's':
      #    categories = budgets.loc[budgets['tracking_type'] == 'withdrawal', ['id','name']]
      #    categories = pd.concat([categories, pd.DataFrame({'name': ['Unknown'], 'id': [-1]})], ignore_index=True)

      #    cat_input = inputs.get_options(list(categories['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")

      #    debits.loc[i, 'Category'] = cat_input
      #    debits.loc[i, 'AssociatedId'] = categories.loc[categories['name'] == cat_input, 'id'].iloc[0]


   for i, row in credits.iterrows():
      if row['IsTransfer'] == 1: continue

      keyword_matches = sql.income.get_id_by_keyword(row['Description'])
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
         categories = incomes[['id','name']]
         categories = pd.concat([categories, pd.DataFrame({'name': ['Unknown'], 'id': [-1]})], ignore_index=True)

         cat_input = inputs.get_options(list(categories['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")
         cat_id = int(categories.loc[categories['name'] == cat_input, 'id'].iloc[0])

         credits.loc[i, 'Category'] = cat_input
         credits.loc[i, 'AssociatedId'] = cat_id

         if cat_id in incomes.loc[budgets['tracking_type'] == 'keyword', ['id']].values:  
            val = 'not blank'
            while val != '':
               val = inputs.get_str("Enter new keyword for category(enter to end): ")
               if val != '':
                  sql.insert_keyword(val, income_id=cat_id)

   print(credits)
   print(debits)
   while inputs.get_yon('Would you like to submit these transactions?') == 'n':
      val = inputs.get_int('Enter index you\'d like to edit: ', 0, max(max(credits.index), max(debits.index)))

      if val in credits.index:
         row = credits.loc[val]
         categories = incomes[['id','name']]
         categories = pd.concat([categories, pd.DataFrame({'name': ['Unknown'], 'id': [-1]})], ignore_index=True)

         cat_input = inputs.get_options(list(categories['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")
         cat_id = int(categories.loc[categories['name'] == cat_input, 'id'].iloc[0])

         credits.loc[val, 'Category'] = cat_input
         credits.loc[val, 'AssociatedId'] = cat_id

      elif val in debits.index:
         row = debits.loc[val]
         categories = budgets[['id','name']]
         categories = pd.concat([categories, pd.DataFrame({'name': ['Unknown'], 'id': [-1]})], ignore_index=True)

         cat_input = inputs.get_options(list(categories['name']), f"Choose Category for the following Transaction:\n\tDesc: {row['Description']}\n\tAmount: {row['DebitOrCredit']}{row['Amount']}")
         cat_id = int(categories.loc[categories['name'] == cat_input, 'id'].iloc[0])

         debits.loc[val, 'Category'] = cat_input
         debits.loc[val, 'AssociatedId'] = cat_id   
         
      print(credits)
      print(debits)


   transactions = pd.concat([debits, credits], ignore_index=True)

   sql.statement.stage_transactions(transactions)

   # sql.close()