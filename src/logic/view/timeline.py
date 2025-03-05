import sys
sys.path.append('./')

import re
from prettytable import PrettyTable
import logic.shared_logic as shared_logic

def timeline():
    def get_dollars_per(per_month):
        return [
            '${:,.2f}'.format(per_month/30.437),
            '${:,.2f}'.format(per_month/4.345),
            '${:,.2f}'.format(per_month),
            '${:,.2f}'.format(per_month*12),
            '${:,.2f}'.format(per_month*60),
        ]

    df = shared_logic.generate_accounts_df()
    
    table = PrettyTable()
    table.align = 'r'
    column_size = 16
    table.field_names = ['Name', 'Percentage', 'Per Day', 'Per Week', 'Per Month', 'Per Year', 'Per 5 Years']
    table.field_names = [name + ' '*((column_size-len(name))//2) for name in table.field_names]

    for cat in df['Category'].unique():
        df_cat = df[df['Category'] == cat]

        table.add_rows([
            ['']*len(table.field_names),
            [f'{str(cat).capitalize()}' + ' '*((column_size-len(str(cat)))//2)]*len(table.field_names),
            ['-'*column_size]*len(table.field_names),
        ])
        table.add_rows([[row[0], f'{row[1]:.2%}'] + get_dollars_per(row[2]) for row in df[df['Category'] == cat].values])
        table.add_rows([['total', f'{sum(df_cat['Percentage']):.2%}'] + get_dollars_per(sum(df_cat['Per Month']))])
    print(table)

    income_percentage_sum = round(df[df['Category'] == 'income']['Percentage'].sum())
    expenses_percentage_sum = round(df[df['Category'] != 'income']['Percentage'].sum())
    income_sum = round(df[df['Category'] == 'income']['Per Month'].sum())
    expenses_sum = round(df[df['Category'] != 'income']['Per Month'].sum())

    if income_percentage_sum != 1:
        print('Warning: Income percentages do not add up to 1.0')
        print(f'Sum: {income_percentage_sum}')

    if expenses_percentage_sum != 1:
        print('Warning: Expenses percentages do not add up to 1.0')
        print(f'Sum: {expenses_percentage_sum}')

    if income_sum != expenses_sum:
        print('Warning: expenses percentages do not add up to income percentages')
        print(f'Sum of expenses: {income_sum}')
        print(f'Sum of income: {expenses_sum}')
