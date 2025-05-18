import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from database.io.dbio import sql
from datetime import timedelta

def pie_chart(start_date='1900-01-01', end_date=''):
   
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
   report['account'] = report['account'].fillna('savings')
   report = report[[col for col in report.columns.tolist() if '_id' not in col]]

   if report.empty: 
      print('No transactions found')
      return

   # print(report.sort_values('account').round(2).reset_index(drop=True))
   # print(report.groupby('account').sum().round(2)[['total_debits', 'total_credits', 'balance']])
   # print()
   # print(report[['total_debits', 'total_credits', 'balance']].sum().round(2))

   by_budget = report.sort_values('account').round(2).reset_index(drop=True)

   # Base colors for each account
   base_colormaps = [
      'Reds', 'Blues', 'Greens', 'Purples', 'Oranges', 'Greys',
      'YlOrBr', 'PuBu', 'BuGn', 'YlGn'
   ]

   # Assign each account a base colormap
   accounts = by_budget['account'].unique()
   account_to_cmap = {
      account: base_colormaps[i % len(base_colormaps)]
      for i, account in enumerate(accounts)
   }

   # For tracking consistent name → color
   name_to_color = {}

   # Group with positive balances only for pie charts
   grouped = by_budget[by_budget['balance'] > 0].groupby('account')
   num_accounts = len(grouped)

   # Create combined figure
   fig = plt.figure(figsize=(4 * num_accounts, 10))
   fig.suptitle(f"Balances by Budget ({start_date} - {end_date})")
   gs = fig.add_gridspec(2, num_accounts)

   # --- PIE CHARTS ---
   for i, (account, group) in enumerate(grouped):
      balances = group['balance']
      cmap_name = account_to_cmap[account]
      cmap = plt.cm.get_cmap(cmap_name)
      shades = cmap(np.linspace(0.4, 0.9, len(group)))

      for name, color in zip(group['name'], shades):
         name_to_color[name] = color

      ax = fig.add_subplot(gs[0, i])
      ax.pie(balances, labels=group['name'], autopct='%1.1f%%', colors=shades)
      ax.set_title(f'Account: {account}')

   # --- BAR GRAPH BELOW PIE CHARTS ---
   ax_bar = fig.add_subplot(gs[1, :])  # Span all columns

   max_balance = by_budget['balance'].max()
   ax_bar.set_xlim(0, max_balance * 1.15)

   bars = ax_bar.barh(
      by_budget['name'], by_budget['balance'],
      color=[name_to_color.get(name, 'gray') for name in by_budget['name']]
   )

   ax_bar.bar_label(bars, fmt='%.0f', padding=3, label_type='edge')
   ax_bar.set_title("Balances by Budget")
   ax_bar.set_xlabel("Balance")

   # Optional: Custom ticks
   # ticks = np.arange(0, max_balance + 100, 100)
   # ax_bar.set_xticks(ticks)
   # ax_bar.set_xticklabels([f"${int(t)}" for t in ticks])
   
   plt.tight_layout()
   plt.show()