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


how do I want to handle updating a past balance?
- delete everything after the update and recreate a new balance at the asof date?
   - Would be difficult to update any transfers between budgets
      - I guess I still need to implement that so I can just keep that in mind

How do I want transfers to work?
- need to have a balance
- select the budget and amount you want to move
- select where it's going
- track when it happened
- create a new balance on the same date + 1 second?
- when updating a past transaction

I think I need to get rid of the balances table, it's making things too complicated
There's no way i'm going to have enough transactions to start slowing things down

How would transfers work if there are no balances?
- we could keep the balance table but only have 1 entery per budget

Ok so we keep the balance table but instead of making sure that everything is accurate and in order, we just create a new balance whenever we say, "create new balance record",
don't keep track of when it is accurate up to, just keep track of the insert_date.
This way we keep change history for the balances, in case we want to go back, while not needing to backtrack and update everything if there was an issue with a past transaction.

With this change we can get rid of the date restrictions on having all records verified

so now the process looks like this
- insert statement
- parse
- verify categories
- create balance
- If we want to update a statement
   - verify that we want to replace the old one
   - delete old transactions
   - parse
   - verify categories
   - create balance using the same statement id

what do I need to do?
1. add statement_id to balance
2. update track statement logic
3. update Run Report logic
   - update asof with insert_date
4. get rid of asof_date on balance

what is the purpose of the balance table?
- keeps a record of the budgets after a given statement as a history
- I think we should actually keep the values from the old statement and mark them in some way unless it was the most recent entry
- They are to track where the income is currently being stored
- A balance for a given statement should always add up to the total at that given time

transfer table
- id
- from_balance_id
- to_balance_id


I think a better option would be to have a second transact table but only for budget transactions, then you can just calculate the 

When I get back I need to update the report logic to update the sql table distribution budget entries
- to do that, will need to figure out how to map the percentage map back to sql, once that is done it should be pretty simple to multiply each of the transactions by the primary distribution
- 

When I get back I need to implement transfers

Next steps, 
- I need to implement a way to add a transfer through User IO
- way to view budgets over a period of time
- rework lp model, get rid of leftovers, try to maximize relative percentages based on overall income
   - Want to be able to apply incomes specified for a specific budget better
   - because right now they're sending alot into leftovers when overflow should be disappearing(this might be a specific problem though and need to deal with it later)