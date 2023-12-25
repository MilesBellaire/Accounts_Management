import subprocess

def main():

    choice = 0

    while choice != 5:
        print()
        print('1. View')
        print('2. Edit Incomes')
        print('3. Edit Budgets')
        print('4. Edit Constants')
        print('5. Exit')
        choice = int(input('Enter your choice: '))

        if choice == 1:
            subprocess.run(['python', 'view.py'])
        elif choice == 2:
            subprocess.run(['python', 'incomes.py'])
        elif choice == 3:
            subprocess.run(['python', 'budgets.py'])
        elif choice == 4:
            subprocess.run(['python', 'constants.py'])


main()