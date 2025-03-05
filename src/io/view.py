import sys
sys.path.append('./')

from logic.view.timeline import timeline
from logic.view.percentages import income_percentages

def view():

    choice = -1

    while choice != 0:
        print()
        print('1. Timeline')
        print('2. Income Percentages')
        print('0. Back')
        choice = int(input('Enter your choice: '))

        if choice == 1:
            timeline()
        elif choice == 2:
            income_percentages()


view()