
-- transfer between accounts to equal
   drop view account_sys_diff;
   create view account_sys_diff as 
   with budgets as (
      select account_id, account, sum(balance) as amount from budget_balance group by account
   ),
   accounts as (
      select ifnull(a.id, 4) as account_id, a.name, round(sum(case when debit_or_credit = '+' then amount else -amount end), 2) as amount 
      from transact t
      left join account a on t.account_id = a.id
      group by a.id, a.name
   )
   select 
      ifnull(ifnull(b.account, a.name), 'savings') account,
      sum(ifnull(b.amount,0.0)) as budget_balance,
      sum(ifnull(a.amount,0.0)) as account_balance, 
      sum(ifnull(b.amount,0.0) - ifnull(a.amount,0.0)) as diff
   from budgets b
   full outer join accounts a
   on a.account_id = b.account_id
   group by ifnull(ifnull(b.account, a.name), 'savings');

-- validate
   select * from account_sys_diff;