

select a.name, round(sum(case when debit_or_credit = '+' then amount else -amount end), 2) as amount 
from transact t
left join account a on t.account_id = a.id
where is_transfer = 0 or transfer_id is not null
group by a.id, a.name;

select sum(balance) from budget_balance;

select round(sum(case when debit_or_credit = '+' then amount else -amount end), 2) as amount 
from transact t
where is_transfer = 0 or transfer_id is not null;
