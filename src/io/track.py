import sys
sys.path.append('./')

from logic.track import track
from inputs import inputs

def track_choices():

    choice = -1

    while choice != 0:
        print()
        print('Incomes Menu')
        print('1. track statement')
        print('0. Back')
        choice = int(input('Enter your choice: '))

        if choice == 1:
            file_name = ''
            if file_name == '': file_name = inputs.get_str("Enter the file name: ")
            track(file_name)

track_choices()