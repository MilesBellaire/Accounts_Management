import pandas as pd
from logic.shared_logic import generate_accounts_df
from database.io.dbio import sql


def update_budget_distribution_weights():
   staged_income = sql.get_transactions_by_income()
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
      return False

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

   return True