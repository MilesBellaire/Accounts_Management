import sys
sys.path.append('./')

import pandas as pd
from inputs import inputs
from database.io.dbio import sql

def transfer_budget():
   budgets = sql.budget_balance.get_all()
   budget_opts = budgets['name'].tolist()
   budget_info = [f"${round(b,2)}" for b in budgets['balance'].tolist()]

   frombudget = inputs.get_options(budget_opts, 'Enter budget to transfer from', budget_info)
   tobudget = inputs.get_options(budget_opts, 'Enter budget to transfer to', budget_info)
   amount = inputs.get_float('Enter amount to transfer', 'amount')

   frombalance = budgets[budgets['name'] == frombudget].iloc[0]['balance']
   tobalance = budgets[budgets['name'] == tobudget].iloc[0]['balance']

   frombudget_id = budgets[budgets['name'] == frombudget].iloc[0]['budget_id']
   tobudget_id = budgets[budgets['name'] == tobudget].iloc[0]['budget_id']

   print(frombudget_id, tobudget_id)

   # Calculate new amounts
   new_frombalance = frombalance - amount
   new_tobalance = tobalance + amount
   
   print()
   print(f'{frombudget} balance: {round(frombalance,2)} -> {round(new_frombalance,2)}')
   print(f'{tobudget} balance: {round(tobalance,2)} -> {round(new_tobalance,2)}')

   # Check if new amounts are valid
   if amount < 0 or new_frombalance < 0:
      print('\nAmount is invalid')
      return
   
   if inputs.get_yon(f'Are you sure you want to complete this transfer?') != 'y':
      return

   sql.budget_balance.insert_transfer(int(frombudget_id), int(tobudget_id), amount)