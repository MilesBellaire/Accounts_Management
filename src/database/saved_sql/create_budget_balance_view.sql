
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

-- Create budget_balance2
   drop view budget_balance;
   create view budget_balance
   as
   select a.name as account, ifnull(b.name, 'undecided') as name, 
      sum(iif(debit_or_credit = '-', amount, 0)) as total_debits,
      sum(iif(debit_or_credit = '+', amount, 0)) as total_credits,
      sum(iif(debit_or_credit = '+', amount, -amount)) as balance,
      account_id, 
      budget_id
   from budget_transact bt
   left join budget b on bt.budget_id = b.id
   left join account a on b.account_id = a.id
   group by a.name, b.name
   union
   select a.name, b.name as budget, 0, 0, 0, account_id, b.id
   from budget b
   join account a on b.account_id = a.id
   where b.id not in (select distinct budget_id from budget_transact)
   order by a.name, b.name;


-- validate
   select * from budget_balance;

   select ifnull(account,'savings'), sum(balance) 
   from budget_balance 
   group by ifnull(account,'savings');
   
   select a.name, round(sum(case when debit_or_credit = '+' then amount else -amount end), 2) as amount 
   from transact t
   left join account a on t.account_id = a.id
   where is_transfer = 0 or transfer_id is not null
   group by a.id, a.name;

   select sum(balance) from budget_balance;

   select round(sum(case when debit_or_credit = '+' then amount else -amount end), 2) as amount 
   from transact t
   where is_transfer = 0 or transfer_id is not null;


