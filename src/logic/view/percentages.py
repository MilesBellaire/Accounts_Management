
from prettytable import PrettyTable
import logic.shared_logic as shared_logic
from database.io.dbio import sql

def income_percentages():
    df = shared_logic.generate_accounts_df()
    df = df.drop(['id'], axis=1)

    budgets = sql.budget.get()

    for i, row in df.iterrows():
        if row['Name'] in budgets['name'].values:
            df.loc[i, 'Account'] = budgets[budgets['name'] == row['Name']]['account'].values[0]
        else:
            df.loc[i, 'Account'] = 'income'
    df.loc[df['Name'] == 'Leftover', 'Account'] = 'savings'

    table = PrettyTable()
    table.align = 'r'
    column_size = 16
    table.field_names = ['Name', 'Overall Percentage', 'Overall Per Month'] + [c.replace('_', ' ').capitalize() for c in df.columns[4:-1].tolist()]
    table.field_names = [name + ' '*((column_size-len(name))//2) for name in table.field_names]

    cats = df[['Account', 'Percentage']].groupby('Account').sum().sort_values('Percentage', ascending=False)
    for cat in cats.index:
        df_cat = df[df['Account'] == cat]

        # print(df_cat.iloc)
        table.add_rows([
            # ['']*len(table.field_names),
            ['-'*column_size]*len(table.field_names),
            [f'{str(cat).capitalize()}' + ' '*((column_size-len(str(cat)))//2)]*len(table.field_names),
            ['']*len(table.field_names),
            # ['-'*column_size]*len(table.field_names)
        ])
        table.add_rows([[row[0], f'{row[1]:.2%}', f"${row[2]:.2f}"] + [f'{row[i+4]:.2%}' if i%2 == 0 else f'${row[i+4]:.2f}' for i in range(len(df.columns)-5)] for row in df_cat.values])
        table.add_rows([['total', f'{sum(df_cat['Percentage']):.2%}', f'${sum(df_cat['Per Month']):.2f}'] + [f'{sum(df_cat.iloc[:, i+4]):.2%}' if i%2 == 0 else f'${sum(df_cat.iloc[:, i+4]):.2f}' for i in range(len(df.columns)-5)]])
    print(table)

    income_percentage_sum = round(df[df['Account'] == 'income']['Percentage'].sum())
    expenses_percentage_sum = round(df[df['Account'] != 'income']['Percentage'].sum())
    income_sum = round(df[df['Account'] == 'income']['Per Month'].sum())
    expenses_sum = round(df[df['Account'] != 'income']['Per Month'].sum())

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
        