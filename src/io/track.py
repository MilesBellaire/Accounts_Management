import sys
sys.path.append('./')

from logic.track import track, run_report
from inputs import inputs

def track_choices():

    choice = -1

    while choice != 0:
        print()
        print('Incomes Menu')
        print('1. track statement')
        print('2. Run Report')
        print('0. Back')
        choice = int(input('Enter your choice: '))

        if choice == 1:
            file_name = ''
            if file_name == '': file_name = inputs.get_str("Enter the file name: ")
            track(file_name)
        elif choice == 2:
            run_report()

track_choices()