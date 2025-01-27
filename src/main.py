import subprocess

def main():

    choice = -1

    while choice != 0:
        print()
        print('1. View')
        print('2. Edit Incomes')
        print('3. Edit Budgets')
        print('4. Edit Constants')
        print('5. Track Incomes')
        print('0. Exit')
        choice = int(input('Enter your choice: '))

        if choice == 1:
            subprocess.run(['python3', './io/view.py'])
        elif choice == 2:
            subprocess.run(['python3', './io/incomes.py'])
        elif choice == 3:
            subprocess.run(['python3', './io/budgets.py'])
        elif choice == 4:
            subprocess.run(['python3', './io/constants.py'])
        elif choice == 5:
            subprocess.run(['python3', './io/track.py'])


main()