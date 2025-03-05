
-- create budget_balance view
   drop view budget_balance;
   create view budget_balance as 
   with credits as (
      select 
         a.id as account_id, 
         a.name as account, 
         b.id as budget_id,
         b.name, 
         sum(t.amount * db.weight) as amount
      from budget b 
      left join account a on b.account_id = a.id
      left join distribution_budget db on db.budget_id = b.id
      left join distribution d on d.id = db.distribution_id
      -- left join income i on i.id = d.income_id
      left join transact t on t.distribution_id = d.id
      where t.debit_or_credit = '+' and is_transfer = 0
      group by a.name, b.id, b.name, a.id
      union all
      select 2, 'savings', 0, 'unassigned', (
         select sum(amount) 
         from transact 
         where is_transfer = 0 and debit_or_credit = '+'
      ) - sum(t.amount * db.weight)
      from transact t
      -- join income i on t.income_id = i.id
      join distribution d on t.distribution_id = d.id
      join distribution_budget db on d.id = db.distribution_id
      join budget b on db.budget_id = b.id
   ),
   debits as (
      select b.account_id, b.id, b.name, sum(amount) as total, min(date) as start_date, max(date) as end_date
      from budget as b
      left join transact as f
      on f.budget_id = b.id
      group by b.name
   ),
   transfers as (
      select 
         credits.budget_id,
         sum(ifnull([from].amount, 0.0)) as out,
         sum(ifnull([to].amount, 0.0)) as [in]
      from credits
      left join budget_balance_transfer bbt
      left join budget_balance_transfer as [from]
      on [from].from_budget_id = credits.budget_id
      left join budget_balance_transfer as [to]
      on [to].to_budget_id = credits.budget_id
      group by credits.budget_id
   )
   select 
      credits.account,
      credits.name,
      ifnull(debits.total,0.0) - transfers.out as total_debits,
      credits.amount + transfers.[in] as total_credits,
      credits.amount - ifnull(debits.total,0.0) - transfers.out + transfers.[in] as balance,
      credits.account_id,
      credits.budget_id
   from credits
   left join debits on credits.budget_id = debits.id
   left join transfers on credits.budget_id = transfers.budget_id
   order by credits.account, credits.name;

-- validate
   select * from budget_balance;

   select account, sum(balance) from budget_balance group by account;

   select a.name, round(sum(case when debit_or_credit = '+' then amount else -amount end), 2) as amount 
   from transact t
   left join account a on t.account_id = a.id
   group by a.id, a.name;

   select sum(balance) from budget_balance;

   select round(sum(case when debit_or_credit = '+' then amount else -amount end), 2) as amount 
   from transact t;

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
      b.account,
      b.amount as budget_balance,
      a.amount as account_balance, 
      b.amount - a.amount as diff
   from budgets b
   join accounts a
   on a.account_id = b.account_id;

-- validate
   select * from account_sys_diff;

--  create transfer table
   drop table budget_balance_transfer;
   create table budget_balance_transfer(
      id integer primary key AUTOINCREMENT,
      amount real,
      from_budget_id integer,
      to_budget_id integer,
      date text,
      foreign key (from_budget_id) references budget(id),
      foreign key (to_budget_id) references budget(id)
   );

SELECT name, type, sql 
FROM sqlite_master 
WHERE type IN ('table', 'view') 
ORDER BY name;

