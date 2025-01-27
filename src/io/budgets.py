
import os
import pandas as pd
from inputs import inputs 
from prettytable import PrettyTable

folder_path = './Csvs'
file_path = './Csvs/budgets.csv'
units = ['$', '%lo-', '%lo+', '%ov']

try:
    df = pd.read_csv(file_path)
except FileNotFoundError:
    df = pd.DataFrame(columns=['name', 'value', 'unit', 'cap', 'equation', 'tags'])
    
    if not os.path.exists('./Csvs'):
        os.makedirs(folder_path)

    df.to_csv(file_path, index=False)

def Save():
    df.to_csv(file_path, index=False)

def Add():
    global df
    name = inputs.get_name()
    unit = inputs.get_unit(units)
    value = inputs.get_value('Enter value in $ per month' if unit == '$' else 'Enter value as %')

    if unit == '%lo-': cap = inputs.get_cap()
    else: cap = None

    if unit == '$' and inputs.get_yon('Do you want to enter an equation?') == 'y': equation = inputs.get_equation()
    else: equation = None

    tags = inputs.get_tags()

    df = pd.concat([df, pd.DataFrame({'name': name, 'value': value, 'unit': unit, 'cap': cap, 'equation': equation, 'tags': tags}, index=[0])], ignore_index=True)
    Save()

def Update():
    global df

    while True:
        name = inputs.get_name()
        if name == 'end': return

        row = df[df['name'] == name]
        if row.empty:
            print(F'{name} not found.')
            continue
        break
    while True:
        column = input('Enter column to update (value, unit, cap, tags): ')
        if column == 'end': return

        if df.columns.str.contains(column).any():
            val = ''
            if column == 'unit':
                val = inputs.get_unit(units)
            elif column == 'value':
                val = inputs.get_value('Enter value in $ per month' if (row['unit'] == '$').any() else 'Enter value as %')
            elif column == 'cap' and row['unit'] == '%lo-':
                val = inputs.get_cap()
            elif column == 'tags':
                val = inputs.get_tags()
            elif column == 'equation' and row['unit'] == '$':
                val = inputs.get_equation()
            df.loc[df['name'] == name, column] = val
            break
        print(f'{column} not found.')

    Save()

def Remove():
    global df
    name = input('Enter name: ')
    df = df[df['name'] != name]
    Save()

def View():
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