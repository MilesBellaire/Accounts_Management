
/*
   budget_id
   transact_id
   date
   distribution_budget_id
   description
   debit_or_credit
   amount
   budget_balance_transfer_id
*/
drop view if exists budget_transact;
create view budget_transact as 
with bt as (
   -- credits
   select 
      t.date, 
      t.description,
      '+' as debit_or_credit,
      t.amount*db.weight as amount,
      t.id as transact_id, 
      db.budget_id, 
      db.id as distribution_budget_id, 
      null as budget_balance_transfer_id
   from transact t
   join distribution d on t.distribution_id = d.id
   join distribution_budget db on d.id = db.distribution_id
   where db.weight <> 0

   union all
   
   -- leftover credits
   select 
      t.date, 
      t.description,
      '+' as debit_or_credit,
      t.amount*(1-sum(db.weight)) as amount,
      t.id as transact_id, 
      0 as budget_id, 
      null as distribution_budget_id, 
      null as budget_balance_transfer_id
   from transact t
   join distribution d on t.distribution_id = d.id
   join distribution_budget db on d.id = db.distribution_id
   group by t.id
   having sum(db.weight) <> 1

   union all

   -- unclassified credits
   select
      t.date, 
      t.description,
      '+' as debit_or_credit,
      t.amount,
      t.id as transact_id, 
      0 as budget_id, 
      null as distribution_budget_id, 
      null as budget_balance_transfer_id
   from transact t
   where income_id = 4

   union all

   -- debits
   select
      t.date, 
      t.description,
      '-' as debit_or_credit,
      t.amount,
      t.id as transact_id, 
      t.budget_id, 
      null as distribution_budget_id, 
      null as budget_balance_transfer_id
   from transact t
   where ifnull(budget_id, '') <> ''

   union all

   -- positive transfers
   select 
      date,
      'transfer' as description,
      '+' as debit_or_credit,
      amount,
      null as transact_id,
      to_budget_id as budget_id,
      null as distribution_budget_id,
      id as budget_balance_transfer_id
   from budget_balance_transfer

   union all

   -- negative transfers
   select 
      date,
      'transfer' as description,
      '-' as debit_or_credit,
      amount,
      null as transact_id,
      from_budget_id as budget_id,
      null as distribution_budget_id,
      id as budget_balance_transfer_id
   from budget_balance_transfer
)
select * from bt
order by date;

select sum(iif(debit_or_credit = '+', amount, -amount))
from budget_transact
where date >= '2024-12-01' and date < '2025-01-01';

select budget_id, sum(iif(debit_or_credit = '+', amount, -amount)) as amount
from budget_transact
where date >= '2024-12-01' and date < '2025-01-01'
group by budget_id;

select * from budget_transact
where date >= '2024-12-01' and date < '2025-01-01';

select sum(iif(debit_or_credit = '+', amount, -amount)) from transact
where date >= '2024-12-01' and date < '2025-01-01';