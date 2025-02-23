Insert all transaction into a transact table

generate report withe all the current budgets balances and spending for each category

Report has
- spending by category
- total spending
- budgets before
- budgets after
- dispursed

I want to to have a staging area where I can load the statement.  Walk away, look at it, edit it, then upload it to the final transactions table.  I don't think it should be going straight into the table, that could cause a lot of errors.  So lets make this staging area

Right now I have the payements loaded in the staging area.  I now need to decide if I want to update with sql or excel.  RN it's going to be sql until I want to make things easier for the user.

So next up I'm can either
- Work on the report
- Connect Track with the rest of the app
- Work on calculating budget percentages
   - Need to decide whether I'm going to look at ideal incomes or actual incomes.  I'm thinking ideal incomes rn.  Not sure how actual incomes would work right now.
- Work on tracking budgets

How am I going to implement balances

I could have a table that stores balances but it would be difficult because my statements come out at different times.  The creditcard statement is up to the 26 and the other accounts are for the whole month.  I guess I could store it up to the 26 and then save the other payements for the next month.  What are some issues with that though?
I would need to figure out when each of the statements are up to, and in order to do that I would need to track which transaction goes to which statements.
Would need to make a new table in the db for that.
Payment transfers could possibly take place over several days(but I've been told that doesn't happen for my cards)
If that happens though I could just make it a pending payment and hold it over aswell.

What do I need to add the the transact table?
- status(pending, complete)
- statement_id

Would need to make a new table for statements
- statement_id
- file_path/filename
- asof_date
- start_date + end_date

Should add a field to show a budget/income or not on the view section
Also one to count it as a balance

Can track balance updates through transactions

Right now I have my total spendings and total income based on account.
I want to know where each of the incomes should be split into each account.
So instead of calculating the amount of money that I would be getting ideally, I should run the percentage algorithm on my actual finances and split it based on that?
I could also 

I get my salary
it gets split into the different account based on the ideal percentages, which would be the same every time.
My balances get updated so I can see how much money is being allocated to each budgetted item
If there is too much in a balance I can adjust the equation I'm using for the budget.
Also, if money starts to pile up in one of the balances, I should have the option to transfer between balances
- To do that there should probably be some kind of balance transfer table that would track that.
- Should only be done for the most recent budgets.
- What would that table track?
   - id
   - source_id
   - dest_id
   - date
   - amount

break shopping into
- clothes
- sporting equipment
- Entertainment
- Self care


When I come back I need to initialize balances create balance report function


Need to update tax to only take from certain things(Salary, interest)

Need to make leftover account so I can say that only certain things can go into it

Need to make a new account and parser for jonhancock