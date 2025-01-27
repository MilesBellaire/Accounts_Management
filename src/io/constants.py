
import os
import pandas as pd
from prettytable import PrettyTable
from inputs import inputs

folder_path = './Csvs'
file_path = './Csvs/constants.csv'

try:
    df = pd.read_csv(file_path)
except FileNotFoundError:
    df = pd.DataFrame(columns=['name', 'value'])
    
    if not os.path.exists('./Csvs'):
        os.makedirs(folder_path)
        
    df.to_csv(file_path, index=False)

def Save():
    df.to_csv(file_path, index=False)

def Add():
    global df

    name = inputs.get_name()
    value = inputs.get_value('Enter value as constant')


    new_row = pd.DataFrame({'name': name, 'value': value}, index=[0])
    df = pd.concat([df, new_row], ignore_index=True)
    Save()

def Update():
    global df

    name = inputs.get_name()
    df.loc[df['name'] == name,'value'] = inputs.get_value('Enter value as constant')
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

    choice = -1

    while choice != 0:
        print()
        print('Constants Menu')
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


constants()