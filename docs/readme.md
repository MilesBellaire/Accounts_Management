# Features
I want an option to enter an expense and then not have to enter it again when you upload the statement

I want to be able to upload a statement and have it categorize all of the items and update balances for those catagories that were saved

I want to be able to section my bank accounts into individual categories with minimal input

Should have a method to edit transactions categories and update balances

# Vacations
To classify vacations, you could enter a time period when you're going to/are on vacation and any travel expenses along with food expenses/shopping expenses that exceed the norm would go there

# Default type
have a csv file that holds keywords for these types of categories
- Like for food, "pizza" would be a keyword
- Travel could have one too with "delta" as a keyword

# Savings
- Whenever the is a withdrawl from saving, it would just ask what it is for since it's difficult to have keywords for these
- Should have an option for moving money from leftovers into other savings accounts

# Combining with Accounts_Management
- Could define a tracking type that would decide if it uses keyword tracking, the savings method, or something else.  Could be another but likely just a specialty section
- Definitely should be taking the categories defined in budgets.csv
- Not really sure how/or if tracking is going to put into the percentage view

# Constants
- Could turn this into variables and could come up with a script that would read some information off the internet to update them for things like gas prices.

# How to initialize tables
- Create budgets
- Create incomes
- Create junction table between budgets and incomes
- Create transactions to initialize bank accounts
- Create balances for each budget and set all amounts to 0
    - ex:
    
|  date | insert_date | description | debit_or_credit | amount | class | budget_id|  income_id|  is_transfer | transfer_id | statement_id | balance_id|  account_id| 
| - | - | - | - | - | - | - | - | - | - | - | - | - |
| 1990-01-21 00:00:00 | 2025-02-20 03:23:52 | initialize account | + | 115.35 | test | NULL | 4 | 0 | NULL | -1 | 0 | 1| 
    - note: income type 4 = other, which assign doesn't assign it to any budgets