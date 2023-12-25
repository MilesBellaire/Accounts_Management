import pandas as pd
import re

class inputs:
    def __init__(self):
        pass

    @staticmethod
    def get_float(prompt: str, label: str) -> float:
        value = ''
        while True:
            try:
                print()
                print(prompt)
                value = float(input(f'Enter {label}: '))
                return value
            except ValueError:
                print('Invalid input. Try again.')
    
    @staticmethod
    def get_name() -> str:
        while True:
            print()
            name = input('Enter name: ').lower().strip()
            if ' ' in name:
                print('Name cannot contain spaces. Try again.')
            else:
                break
        return name
    
    @staticmethod
    def get_value(prompt: str) -> float:
        value = inputs.get_float(prompt, 'value')
        return value
    
    @staticmethod
    def get_unit(possible_units: list) -> str:
        unit = ''
        while True:
            print()
            print(f'Possible units: {possible_units}')
            unit = input('Enter unit: ')
            if unit in possible_units:
                break
            print('Invalid unit. Try again.')
        return unit
    
    @staticmethod
    def get_cap() -> float:
        while True:
            cap = inputs.get_float('Enter as $ per month', 'cap')
            if cap > 0:
                break
        return cap
    
    @staticmethod
    def get_tags() -> list:
        # tags_input = ''
        # tags = []
        # while tags_input != 'end':
        #     print()
        #     print('Enter end when you\'re done entering tags')
        #     tags_input = input('Enter tags: ')
        #     if tags_input != 'end':
        #         tags.append(tags_input)

        
        print()
        tags = input('Enter tags: ')
        return tags

    @staticmethod
    def get_equation() -> str:
        constants = pd.read_csv('./Csvs/constants.csv')['name'].tolist()

        while True:
            print()
            print('Format equation as: [self] + [const name] * [other const name]')
            print('Allowed operations: +, -, *, /')
            print(f'Possible constants: {constants}')
            equation = input('Enter equation: ')
            
            split_equation = re.split(r'[\*\+/\\-]', equation.replace(' ', ''))
            print(f'Split equation: {split_equation}')
            contains_self = False
            invalid = False
            for split in split_equation:
                if split[0] == '[' and split[-1] == ']':
                    if split[1:-1] == 'self':
                        contains_self = True
                    elif split[1:-1] not in constants:
                        print('Invalid constant. Try again.')
                        invalid = True
                        break
                else:
                    try:
                        float(split)
                    except:
                        print('Invalid equation. Try again.')
                        invalid = True
                        break
            if not invalid and contains_self:
                break
        return equation
    
    def get_yon(prompt):
        yon = ''
        while yon != 'y' and yon != 'n':
            print()
            print(prompt)
            yon = input('Enter y or n: ')
            if yon != 'y' and yon != 'n':
                print('Invalid input. Try again.')
        return yon
    
    def get_dollars_per_hour():
        while True:
            try:
                print()
                print('Enter value in $ per hour')
                value = float(input('Enter value: '))
                return value
            except ValueError:
                print('Invalid input. Try again.')
    
    def get_hours():
        while True:
            try:
                print()
                print('Enter value in hours')
                value = float(input('Enter value: '))
                return value
            except ValueError:
                print('Invalid input. Try again.')
