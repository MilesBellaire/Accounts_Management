import pandas as pd
from prettytable import PrettyTable
from inputs import inputs

file_path = './Csvs/incomes.csv'

try:
    df = pd.read_csv(file_path)
except FileNotFoundError:
    df = pd.DataFrame(columns=['name', '$perhour', 'hours'])
    df.to_csv(file_path, index=False)

def Save():
    df.to_csv(file_path, index=False)

def Add():
    global df

    name = inputs.get_name()
    dollars_per_hour = inputs.get_dollars_per_hour()
    hours = inputs.get_hours()

    new_row = pd.DataFrame({'name': name, '$perhour': dollars_per_hour, 'hours': hours}, index=[0])
    df = pd.concat([df, new_row], ignore_index=True)
    Save()

def Update():
    global df

    while True:
        name = inputs.get_name()
        row = df[df['name'] == name]
        if row.empty:
            print(F'{name} not found.')
            continue
        break
    while True:
        column = input('Enter column to update ($perhour, hours): ')

        if column in df.columns.tolist():
            val = ''
            if column == '$perhour':
                val = inputs.get_dollars_per_hour()
            elif column == 'hours':
                val = inputs.get_hours()
            df.loc[df['name'] == name, column] = val
            break
        print(f'{column} not found.')
    Save()

def Remove():
    global df

    name = inputs.get_name()
    df = df[df['name'] != name]
    df.to_csv(file_path, index=False)
    Save()

def View():
    table = PrettyTable()
    table.align = 'r'
    table.field_names = df.columns
    table.add_rows(df.values.tolist())
    print(table)

def constants():

    choice = 0

    while choice != 5:
        print()
        print('Incomes Menu')
        print('1. View')
        print('2. Add')
        print('3. Update')
        print('4. Remove')
        print('5. Back')
        choice = int(input('Enter your choice: '))

        if choice == 1:
            View()
        elif choice == 2:
            Add()
        elif choice == 3:
            Update()
        elif choice == 4:
            Remove()


constants()