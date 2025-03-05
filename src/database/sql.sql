-- select distinct  from budget_transact;
select 
   a.name as account,
   ifnull(b.name, 'undecided') as name,
   sum(iif(bt.debit_or_credit = '+', 0, bt.amount)) as total_debits,
   sum(iif(bt.debit_or_credit = '+', bt.amount, 0)) as total_credits,
   sum(iif(bt.debit_or_credit = '+', bt.amount, -bt.amount)) as balance,
   a.id as account_id,
   b.id as budget_id
from budget_transact bt
left join budget b on bt.budget_id = b.id
left join transact t on bt.transact_id = t.id
left join account a on b.account_id = a.id
-- where bt.date >= '{start[0]}-{start[1]}-{start[2]} 00:00:00' and bt.date < '{end[0]}-{end[1]}-{end[2]} 00:00:00'
group by a.name, b.name