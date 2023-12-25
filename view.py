import re
import pandas as pd
from prettytable import PrettyTable

incomes = pd.read_csv('./Csvs/incomes.csv')
budgets = pd.read_csv('./Csvs/budgets.csv')
constants = pd.read_csv('./Csvs/constants.csv')

def Evaluate_equation(equation: str, base: float)-> float:
    if equation == 'nan': return base
    split_equation = re.split(r'[\[\]]', equation.replace(' ', ''))
    filled_equation = ''

    for split in split_equation:
        if split == 'self' or split in constants['name'].tolist():
            if split == 'self':
                filled_equation += str(base)
            else:
                filled_equation += str(constants[constants['name'] == split]['value'].iloc[0])
        else:
            filled_equation += split
    return eval(filled_equation)

def get_dollars_per(per_month):
    return [
        '${:,.2f}'.format(per_month/30.437),
        '${:,.2f}'.format(per_month/4.345),
        '${:,.2f}'.format(per_month),
        '${:,.2f}'.format(per_month*12),
        '${:,.2f}'.format(per_month*60),
    ]
    
def generate_accounts_df():
    columns = ['Name', 'Percentage', 'Per Month', 'Category']

    income_per_month = sum(incomes['$perhour'])*sum(incomes['hours'])*4.345

    expenses_per_month = (sum(budgets[budgets['unit'] == '%ov']['value']/100*income_per_month)
        + sum([Evaluate_equation(str(budget[5]), budget[1]) for budget in budgets[budgets['unit'] == '$'].values]))
    
    leftover = income_per_month-expenses_per_month

    percent_cut_by_cap = 0
    overall_leftover_percentage = 1

    # Incomes
    accounts = [[
        income[0], 
        income[1]*income[2]*4.345/income_per_month, 
        income[1]*income[2]*4.345, 
        'income'
    ] for income in incomes.values]

    # Over Percentages
    accounts += [[
        budget[0],
        budget[1]/100,
        budget[1]/100*income_per_month,
        budget[4]
    ] for budget in budgets[budgets['unit'] == '%ov'].values]
    
    # Flat Expenses
    for budget in budgets[budgets['unit'] == '$'].values:
        expense = Evaluate_equation(str(budget[5]), budget[1])
        accounts.append([
            budget[0],
            expense/income_per_month,
            expense,
            budget[4]
        ])
    
    # Leftover percentages with caps
    for budget in budgets[budgets['unit'] == '%lo-'].values:
        expense = max(min(budget[1]/100*leftover, budget[3]), 0)
        percentage = expense/income_per_month

        accounts.append([
            budget[0],
            percentage,
            expense,
            budget[4]
        ])
        
        percent_cut_by_cap += max((budget[1]/100-expense/leftover), 0)

    # Leftover percentages that take over other's caps
    for budget in budgets[budgets['unit'] == '%lo+'].values:
        additional_percentage = percent_cut_by_cap/len(budgets[budgets['unit'] == '%lo+'])
        leftover_percentage = budget[1]/100 + additional_percentage
        percentage = leftover_percentage*leftover/income_per_month
        expense = percentage*income_per_month

        accounts.append([
            budget[0],
            percentage,
            expense,
            budget[4]
        ])

    # Leftovers
    overall_leftover_percentage = 1-sum([account[1] for account in accounts if account[3] != 'income'])
    accounts.append([
        'Leftover',
        overall_leftover_percentage,
        max(overall_leftover_percentage*(income_per_month), 0),
        'savings'
    ])
    
    return pd.DataFrame(accounts, columns=columns)

def overall_percentages():
    df = generate_accounts_df()
    
    table = PrettyTable()
    table.align = 'r'
    column_size = 16
    table.field_names = ['Name', 'Percentage', 'Per Day', 'Per Week', 'Per Month', 'Per Year', 'Per 5 Years']
    table.field_names = [name + ' '*((column_size-len(name))//2) for name in table.field_names]

    for cat in df['Category'].unique():
        table.add_rows([
            ['']*len(table.field_names),
            [f'{str(cat).capitalize()}' + ' '*((column_size-len(cat))//2)]*len(table.field_names),
            ['-'*column_size]*len(table.field_names)
        ])
        table.add_rows([[row[0], f'{row[1]:.2%}'] + get_dollars_per(row[2]) for row in df[df['Category'] == cat].values])
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
        
def Display():
    
    column_sizes = {
        'Name': 20,
        'Value': 18,
        'Per Day': 14,
        'Per Week': 14,
        'Per Month': 14,
        'Per Year': 14,
        'Per 5 Years': 14,
        'Category': 20
    }
    empty_row = ['', '', '', '', '', '', '', '', '']

    income_table = PrettyTable()
    income_table.align = 'r'
    income_table.field_names = ['Income', '$PerHour', 'Hours', 'Per Day', 'Per Week', 'Per Month', 'Per Year', 'Per 5 Years']
    income_table.min_width['Income'] = column_sizes['Name']
    income_table.min_width['$PerHour'] = column_sizes['Value']//2
    income_table.min_width['Hours'] = column_sizes['Value']//2
    income_table.min_width['Per Day'] = column_sizes['Per Day']
    income_table.min_width['Per Week'] = column_sizes['Per Week']
    income_table.min_width['Per Month'] = column_sizes['Per Month']
    income_table.min_width['Per Year'] = column_sizes['Per Year']
    income_table.min_width['Per 5 Years'] = column_sizes['Per 5 Years']

    budget_table = PrettyTable()
    budget_table.align = 'r'
    budget_table.field_names = ['Budget', 'Value', 'units', 'Per Day', 'Per Week', 'Per Month', 'Per Year', 'Per 5 Years', 'Category']
    budget_table.min_width['Budget'] = column_sizes['Name']
    budget_table.min_width['Value'] = column_sizes['Value']//2
    budget_table.min_width['units'] = column_sizes['Value']//2
    budget_table.min_width['Per Day'] = column_sizes['Per Day']
    budget_table.min_width['Per Week'] = column_sizes['Per Week']
    budget_table.min_width['Per Month'] = column_sizes['Per Month']
    budget_table.min_width['Per Year'] = column_sizes['Per Year']
    budget_table.min_width['Per 5 Years'] = column_sizes['Per 5 Years']

    income_per_month = 0
    for income in incomes.values:
        income_per_month += income[1]*income[2]*4.345
        income_table.add_row([income[0], '$'+str(income[1]), income[2]] + get_dollars_per(income[1]*income[2]*4.345))
    
    expenses_per_month = []
    for budget in budgets[budgets['unit'] == '%ov'].values:
        expenses_per_month.append(budget[1]/100*income_per_month)
        budget_table.add_row([budget[0], str(round(budget[1], 1))+budget[2][0], budget[2]] + get_dollars_per(expenses_per_month[-1]) + [budget[4]])

    budget_table.add_row(empty_row)

    for budget in budgets[budgets['unit'] == '$'].values:
        expenses_per_month.append(Evaluate_equation(str(budget[5]), budget[1]))
        budget_table.add_row([budget[0], budget[2][0]+str(round(budget[1], 2)), budget[2]] + get_dollars_per(expenses_per_month[-1]) + [budget[4]])

    budget_table.add_row(empty_row)

    leftover = income_per_month-sum(expenses_per_month)

    percent_cut_by_cap = 0
    leftover_percentage = 1
    for budget in budgets[budgets['unit'] == '%lo-'].values:
        expense = max(min(budget[1]/100*leftover, budget[3]), 0)
        percentage = expense/(leftover)*100
        percent_cut_by_cap += max((budget[1]-percentage)/100, 0)
        leftover_percentage -= percentage/100
        budget_table.add_row([budget[0], str(round(percentage,2))+budget[2][0], budget[2]] + get_dollars_per(expense) + [budget[4]])
    
    budget_table.add_row(empty_row)

    for budget in budgets[budgets['unit'] == '%lo+'].values:
        additional_percentage = percent_cut_by_cap/len(budgets[budgets['unit'] == '%lo+'])
        percentage = budget[1]/100 + additional_percentage
        leftover_percentage -= percentage
        expense = max(min(percentage*(leftover), budget[3]), 0)
        budget_table.add_row([budget[0], str(round(percentage*100, 2))+budget[2][0], budget[2]] + get_dollars_per(expense) + [budget[4]])

    budget_table.add_row(empty_row)

    expense = max(leftover_percentage*(leftover), 0)
    budget_table.add_row(['Leftover', str(round(leftover_percentage*100, 2))+'%', '%lo++'] + get_dollars_per(expense) + [budget[4]])

    print(income_table)
    print()
    print(budget_table)
    print()
    print(f'Money after essential costs per month: {round(leftover)}')


def view():

    choice = 0

    while choice != 3:
        print()
        print('1. Display')
        print('2. Overall Percentages')
        print('3. Back')
        choice = int(input('Enter your choice: '))

        if choice == 1:
            Display()
        elif choice == 2:
            overall_percentages()


view()