import sys
sys.path.append('./')

import pandas as pd
from database.io.dbio import sql
import re
from logic.shared_logic import Evaluate_equation

class inputs:
    def __init__(self):
        pass
    
    @staticmethod
    def _validate_initial_input(value):
        if value == 'q': exit()
        return value
    @staticmethod
    def get_float(prompt: str, label: str) -> float:
        value = ''
        while True:
            try:
                print()
                print(prompt)
                value = input(f'Enter {label}: ')
                value = inputs._validate_initial_input(value)

                value = float(value)
                return value
            except ValueError:
                print('Invalid input. Try again.')

    @staticmethod
    def get_str(prompt: str) -> str:
        value = ''
        while True:
            try:
                print()
                value = input(prompt)
                value = inputs._validate_initial_input(value)

                value = str(value)
                return value
            except ValueError:
                print('Invalid input. Try again.')
    

    @staticmethod
    def get_int(prompt: str, lower_bound=None, upper_bound=None) -> int:
        value = ''
        while True:
            try:
                print()
                value = input(prompt)
                value = inputs._validate_initial_input(value)

                value = int(value)
                if lower_bound is not None and value < lower_bound:
                    print('Invalid input. Try again.')
                elif upper_bound is not None and value > upper_bound:
                    print('Invalid input. Try again.')
                else:
                    return value
            except ValueError:
                print('Invalid input. Try again.')

    @staticmethod
    def get_options(options, prompt, additional_info=None):
        while True:
            print()
            print(prompt)
            print('Possible options:')
            for i, option in enumerate(options):
                print(f'{i}: {option}{" - "+additional_info[i] if additional_info is not None else ""}')
            try:
                index = input('Enter index: ')
                index = inputs._validate_initial_input(index)

                index = int(index)
                if index < 0 or index >= len(options):
                    print('Invalid choice. Try again.')
                else:
                    return options[index]
            except ValueError:
                print('Invalid input. Try again.')

    @staticmethod
    def get_name(existing_names=[]) -> str:
        while True:
            name = inputs.get_str('Enter name: ').lower().strip()
            if ' ' in name:
                print('Name cannot contain spaces.')
            elif name in existing_names:
                print('Name already exists.')
            else:
                break
        return name
    
    @staticmethod
    def get_value(prompt: str) -> float:
        value = inputs.get_float(prompt, 'value')
        return value
    
    @staticmethod
    def get_unit(possible_units: list) -> str:
        unit = inputs.get_options(possible_units, 'Enter unit')
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
        tags = inputs.get_str('Enter tags: ')
        return tags

    @staticmethod
    def get_equation() -> str:
        constants = sql.get_constants()['name'].tolist()
        incomes = sql.income.get()
        incomes = incomes[(incomes['unit'] == '$') | (incomes['unit'] == 'eq')]['name'].tolist()
        budgets = sql.budget.get()
        budgets = budgets[(budgets['unit'] == '$') | (budgets['unit'] == 'eq')]['name'].tolist()

        while True:
            print()
            print('Format equation as: [self] + [var name] * [other const name]')
            print('Allowed operations: +, -, *, /')
            print(f'Possible variables: {constants+incomes+budgets}')
            equation = input('Enter equation: ')
            equation = inputs._validate_initial_input(equation)
            
            split_equation = re.split(r'[\*\+/\\-]', equation.replace(' ', ''))
            print(f'Split equation: {split_equation}')
            contains_self = False
            invalid = False
            for split in split_equation:
                if split[0] == '[' and split[-1] == ']':
                    if split[1:-1] == 'self':
                        contains_self = True
                #     elif split[1:-1] not in constants:
                #         print('Invalid constant. Try again.')
                #         invalid = True
                #         break
                # else:
                #     try:
                #         float(split)
                #     except:
                #         print('Invalid equation. Try again.')
                #         invalid = True
                #         break
            try:
                Evaluate_equation(equation, 0)
            except ValueError:
                print(ValueError)
                print('Invalid equation. Try again.')
                invalid = True
            
            if not invalid and contains_self:
                break
        return equation
    
    @staticmethod
    def get_yon(prompt):
        yon = ''
        while yon != 'y' and yon != 'n':
            print()
            print(prompt)
            yon = input('Enter y or n: ')
            inputs._validate_initial_input(yon)
            if yon != 'y' and yon != 'n':
                print('Invalid input. Try again.')
        return yon
    
    @staticmethod
    def get_dollars_per_hour():
        return inputs.get_float('Enter value in $ per hour', 'value')
    
    @staticmethod
    def get_hours():
        return inputs.get_float('Enter value in hours', 'value')
    
    # Not sure this works
    @staticmethod
    def get_date(prompt):
        while True:
            date = inputs.get_str(prompt)
            if len(date) == 8 and date[2] == '-' and date[5] == '-':
                break
            print('Invalid date format. Try again.')
        return date
    
    @staticmethod
    def get_month(prompt):
        while True:
            date = inputs.get_str(prompt)
            # validate that date is a valid date and is in the form of YYYY-MM
            try:
                pd.to_datetime(date, format='%Y-%m')
            except ValueError:
                print('Invalid date format. Try again.')
                continue
            break
        return date

    @staticmethod
    def multi_select(options: list, prompt: str, num_required=0, selected=[]) -> list:
        while True:
            print()
            print(prompt)
            print('Select options:')
            for i, option in enumerate(options):
                print(f'{'-' if i in selected else ' '} {i}: {option}')
            try:
                index = input('Enter index: ')
                index = inputs._validate_initial_input(index)

                if not index and num_required <= len(selected) and inputs.get_yon('Confirm?') == 'y':
                    break
                elif not index and num_required > len(selected):
                    print(f'{num_required} options required.')
                    continue
                index = int(index)
                if index < 0 or index >= len(options):
                    print('Invalid choice. Try again.')
                elif index in selected:
                    selected.remove(index)
                else:
                    selected.append(index)
            except ValueError:
                print('Invalid input. Try again.')
        return [options[i] for i in selected]