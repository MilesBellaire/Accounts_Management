

-- select a.name, round(sum(case when debit_or_credit = '+' then amount else -amount end), 2) as amount 
-- from transact t
-- left join account a on t.account_id = a.id
-- where is_transfer = 0 or transfer_id is not null
-- group by a.id, a.name;

-- select sum(balance) from budget_balance;

-- select round(sum(case when debit_or_credit = '+' then amount else -amount end), 2) as amount 
-- from transact t
-- where is_transfer = 0 or transfer_id is not null;


-- select *
-- from distribution_budget
-- where distribution_id = (select primary_distribution_id from income where id = 9)
--    and budget_id = 2;

UPDATE transact as t1
SET transfer_id = (
   SELECT t2.id
   FROM transact AS t2
   WHERE t1.amount = t2.amount
   AND t2.is_transfer = 1
   AND (
      strftime('%Y', t1.date) = strftime('%Y', t2.date) and
      strftime('%m', t1.date) = strftime('%m', t2.date) and 
      abs(strftime('%d', t1.date) - strftime('%d', t2.date)) <= 2
   )
   AND t1.debit_or_credit <> t2.debit_or_credit
   AND t2.transfer_id IS NULL or t2.transfer_id = t1.id
   limit 1
)
WHERE transfer_id IS NULL and is_transfer = 1;

select * from transact
where id = 769;