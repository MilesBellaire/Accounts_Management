import sys
sys.path.append('./')

from database.io.dbio import sql
from inputs import inputs 
from prettytable import PrettyTable

units = sql.income.get_units().astype({'id': int})
unit_opts = units['abv'].tolist()

tracking_types = sql.get_tracking_types().astype({'id': int})
tracking_type_opts = tracking_types['name'].tolist()

budgets = sql.budget.get()
budget_opts = budgets['name'].tolist()

def Add():
    incomes = sql.income.get()

    name = inputs.get_name(incomes['name'].tolist())
    unit = inputs.get_unit(unit_opts)
    value = inputs.get_value('Enter value in $ per month' if unit in ('$','eq') else 'Enter value as %')

    if unit == 'eq' and inputs.get_yon('Do you want to enter an equation?') == 'y': 
        equation = inputs.get_equation()
    else: equation = None

    tracking_type = inputs.get_options(tracking_type_opts, 'Enter tracking type')
    tags = inputs.get_tags()

    attached_budgets = inputs.multi_select(budget_opts, 'Enter budgets that this income will contribute to')

    sql.income.insert(
        name, 
        equation, 
        tags, 
        tracking_types[tracking_types['name'] == tracking_type].iloc[0]['id'], 
        units[units['abv'] == unit].iloc[0]['id'], 
        value,
        [budgets[budgets['name'] == budget].iloc[0]['id'] for budget in attached_budgets]
    )

def Update():
    # turn nans in to none
    incomes = sql.income.get().fillna('')
    income_opts = incomes['name'].tolist()

    income = inputs.get_options(income_opts, 'Enter income to update')

    row = incomes[incomes['name'] == income].iloc[0]
    
    column = inputs.get_options([
        'name',
        'unit',
        'value',
        'tags',
        'tracking_type',
    ] + (['equation'] if row['unit'] == 'eq' else [])
    , 'Enter column to update')

    val = ''
    if column == 'name':
        val = inputs.get_name(income_opts)
    elif column == 'unit':
        val = inputs.get_unit(unit_opts)
        if val == 'eq': row['equation'] = inputs.get_equation()
    elif column == 'value':
        val = inputs.get_value('Enter value in $ per month' if (row['unit'] == '$') else 'Enter value as %')
    elif column == 'tags':
        val = inputs.get_tags()
    elif column == 'equation' and row['unit'] == 'eq':
        val = inputs.get_equation()
    elif column == 'tracking_type':
        val = inputs.get_options(tracking_type_opts, 'Enter tracking type')
    row[column] = val

    sql.income.update(
        row['id'], 
        row['name'], 
        row['equation'], 
        row['tags'], 
        tracking_types[tracking_types['name'] == row['tracking_type']].iloc[0]['id'], 
        units[units['abv'] == row['unit']].iloc[0]['id'], 
        row['value']
    )


def Remove():
    incomes = sql.income.get()
    income_opts = incomes['name'].tolist()

    income = inputs.get_options(income_opts, 'Enter income to remove')

    if inputs.get_yon(f'Are you sure you want to remove {income}?') != 'y':
        return
    sql.income.delete(incomes[incomes['name'] == income].iloc[0]['id'])

def View():
    df = sql.income.get()

    table = PrettyTable()
    table.align = 'r'
    table.field_names = df.columns
    table.add_rows(df.values.tolist())
    table.max_width['budgets'] = 50
    print(table)

def incomes():

    choice = -1

    while choice != 0:
        print()
        print('Incomes Menu')
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


incomes()