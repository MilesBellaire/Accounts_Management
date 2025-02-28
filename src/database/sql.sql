
select * from statement;

-- start_date: '2024-12-01 00:00:00'
-- end_date: datetime('now')

delete from budget_balance_transfer;

-- insert into budget_balance_transfer(amount, from_budget_id, to_budget_id, date)
-- values (10000.00, 0, 2, '2024-12-01 00:00:00');


select * from transact
where date >= '2024-12-01 00:00:00' and date < '2024-12-31 00:00:00'
   and debit_or_credit = '+';

with trans as (
   select * from transact
   where date >= '2024-12-01 00:00:00' and date < '2024-12-31 00:00:00'
),
credits as (
   select 
      a.id as account_id, 
      a.name as account, 
      b.id as budget_id,
      b.name, 
      sum(ifnull(t.amount,0.0) * ifnull(db.weight,0.0)) as amount
   from budget b 
   left join account a on b.account_id = a.id
   left join distribution_budget db on db.budget_id = b.id
   left join distribution d on d.id = db.distribution_id
   left join income i on i.primary_distribution_id = d.id
   left join trans t on t.income_id = i.id 
      and t.debit_or_credit = '+' and is_transfer = 0
   group by a.name, b.id, b.name, a.id
   union all
   select
      2,
      'savings', 
      0, 
      'unassigned', 
   (
      select sum(amount) 
      from trans 
      where is_transfer = 0 and debit_or_credit = '+'
   ) - sum(t.amount * db.weight)
   from trans t
   join income i on t.income_id = i.id
   join distribution d on i.primary_distribution_id = d.id
   join distribution_budget db on d.id = db.distribution_id
   join budget b on db.budget_id = b.id
),
debits as (
   select b.account_id, b.id, b.name, sum(amount) as total, min(date) as start_date, max(date) as end_date
   from budget as b
   left join trans as f
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
