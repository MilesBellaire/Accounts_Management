import sys
sys.path.append('./')

from database.io.dbio import sql
from inputs import inputs 
from prettytable import PrettyTable

units = sql.budget.get_units().astype({'id': int})
unit_opts = units['abv'].tolist()

tracking_types = sql.get_tracking_types().astype({'id': int})
tracking_type_opts = tracking_types['name'].tolist()

accounts = sql.get_accounts().astype({'id': int})
account_opts = accounts['name'].tolist()

incomes = sql.income.get()
income_opts = incomes['name'].tolist()

def Add():
    budgets = sql.budget.get()


    name = inputs.get_name(budgets['name'].tolist())
    unit = inputs.get_unit(unit_opts)
    value = inputs.get_value('Enter value in $ per month' if unit in ('$', 'eq') else 'Enter value as %')

    if unit == '%lo-': cap = inputs.get_cap()
    else: cap = None

    if unit == 'eq': # and inputs.get_yon('Do you want to enter an equation?') == 'y': 
        equation = inputs.get_equation()
    else: equation = None

    tracking_type = inputs.get_options(tracking_type_opts, 'Enter tracking type')
    account = inputs.get_options(account_opts, 'Enter account')
    tags = inputs.get_tags()

    attached_incomes = inputs.multi_select(income_opts, 'Enter incomes that will contribute to this budget')

    new_id = sql.budget.insert(
        name, 
        equation, 
        tags, 
        tracking_types[tracking_types['name'] == tracking_type].iloc[0]['id'], 
        units[units['abv'] == unit].iloc[0]['id'], 
        value, 
        cap,
        accounts[accounts['name'] == account].iloc[0]['id']
    )

    for income in attached_incomes:
        sql.insert_distribution_budget(
            incomes[incomes['name'] == income].iloc[0]['id'],
            new_id
        )

def Update():
    # turn nans in to none
    budgets = sql.budget.get().fillna('')
    budget_opts = budgets['name'].tolist()

    budget = inputs.get_options(budget_opts, 'Enter budget to update')

    row = budgets[budgets['name'] == budget].iloc[0]
    
    column = inputs.get_options([
        'name',
        'unit',
        'value',
        'tags',
        'tracking_type',
        'account',
    ] + (['equation'] if row['unit'] == 'eq' else [])
    + (['cap'] if row['unit'] == '%lo-' else [])
    , 'Enter column to update')

    val = ''
    if column == 'name':
        val = inputs.get_name(budget_opts)
    elif column == 'unit':
        val = inputs.get_unit(unit_opts)
        if val == 'eq': row['equation'] = inputs.get_equation()
    elif column == 'value':
        val = inputs.get_value('Enter value in $ per month' if (row['unit'] == '$') else 'Enter value as %')
    elif column == 'cap' and row['unit'] == '%lo-':
        val = inputs.get_cap()
    elif column == 'tags':
        val = inputs.get_tags()
    elif column == 'equation' and row['unit'] == 'eq':
        val = inputs.get_equation()
    elif column == 'tracking_type':
        val = inputs.get_options(tracking_type_opts, 'Enter tracking type')
    elif column == 'account':
        val = inputs.get_options(account_opts, 'Enter account')
    row[column] = val

    sql.budget.update(
        row['id'], 
        row['name'], 
        row['equation'], 
        row['tags'], 
        tracking_types[tracking_types['name'] == row['tracking_type']].iloc[0]['id'], 
        units[units['abv'] == row['unit']].iloc[0]['id'], 
        row['value'], 
        row['cap'], 
        accounts[accounts['name'] == row['account']].iloc[0]['id']
    )


def Remove():
    budgets = sql.budget.get()
    budget_opts = budgets['name'].tolist()

    budget = inputs.get_options(budget_opts, 'Enter budget to remove')

    if inputs.get_yon(f'Are you sure you want to remove {budget}?') != 'y':
        return
    sql.budget.delete(budgets[budgets['name'] == budget].iloc[0]['id'])

def View():
    df = sql.budget.get()

    table = PrettyTable()
    table.align = 'r'
    table.field_names = df.columns
    table.add_rows(df.values.tolist())
    print(table)

def budgets():

    choice = -1

    while choice != 0:
        print()
        print('Budgets Menu')
        print('1. View')
        print('2. Add')
        print('3. Update')
        print('4. Remove')
        print('0. Back')
        choice = int(input('Enter your choice: '))

        if choice == 1:
            View()
        elif choice == 2:
            Add()
        elif choice == 3:
            Update()
        elif choice == 4:
            Remove()


budgets()