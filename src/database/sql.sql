-- update transact
-- set income_id = 1
-- where id = 595;

select 
   a.name as account,
   ifnull(b.name, 'undecided') as name,
   sum(iif(bt.debit_or_credit = '+', ifnull(bt.amount, 0), ifnull(-bt.amount,0))) as balance,
   a.id as account_id,
   b.id as budget_id
from budget_transact bt
left join budget b on bt.budget_id = b.id
left join transact t on bt.transact_id = t.id
left join account a on b.account_id = a.id
where bt.date < '2025-01-28 00:00:00'
group by a.name, b.name;

with initial_budget as (
   select 
      a.name as account,
      ifnull(b.name, 'undecided') as name,
      sum(iif(bt.debit_or_credit = '+', ifnull(bt.amount, 0), ifnull(-bt.amount,0))) as balance,
      a.id as account_id,
      b.id as budget_id
   from budget_transact bt
   left join budget b on bt.budget_id = b.id
   left join transact t on bt.transact_id = t.id
   left join account a on b.account_id = a.id
   where bt.date < '2025-01-28 00:00:00'
   group by a.name, b.name
),
new_balance as (
   select 
      a.name as account,
      ifnull(b.name, 'undecided') as name,
      ifnull(ib.balance,0.0) as initial_balance,
      sum(iif(bt.debit_or_credit = '+', 0, bt.amount)) as total_debits,
      sum(iif(bt.debit_or_credit = '+', bt.amount, 0)) as total_credits,
      sum(iif(bt.debit_or_credit = '+', bt.amount, -bt.amount)) as change,
      sum(iif(bt.debit_or_credit = '+', bt.amount, -bt.amount)) + ifnull(ib.balance,0) as balance,
      a.id as account_id,
      b.id as budget_id
   from budget_transact bt
   left join budget b on bt.budget_id = b.id
   left join transact t on bt.transact_id = t.id
   left join account a on b.account_id = a.id
   left join initial_budget ib on ifnull(b.name, 'undecided') = ib.name
   where bt.date >= '2025-01-28 00:00:00' and bt.date < '2025-03-01 00:00:00'
   group by a.name, b.name, ib.balance
   order by a.name, b.name
)
select *
from new_balance;

select *
from budget_transact
where budget_id = 2;

select *
from s