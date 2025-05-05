import sys
sys.path.append('./')

from logic.track.track import track
from logic.track.run_report import run_report
from logic.track.budget_transfer import transfer_budget
from inputs import inputs
import pandas as pd

def track_choices():

    choice = -1

    while choice != 0:
        print()
        print('Incomes Menu')
        print('1. track statement')
        print('2. Run Report asof today')
        print('3. Run Report by month')
        print('4. Transfer Budgets')
        print('0. Back')
        choice = int(input('Enter your choice: '))

        if choice == 1:
            file_name = ''
            if file_name == '': file_name = inputs.get_str("Enter the file name: ")
            track(file_name)
        elif choice == 2:
            run_report()
        elif choice == 3:
            month = inputs.get_month('Enter month in YYYY-MM format: ')
            next_month = str(pd.to_datetime(month).to_period('M') + 1)
            # print(next_month)
            run_report(month, next_month)
        elif choice == 4:
            transfer_budget()

track_choices()