-- update transact
-- set is_transfer = 0,
--    income_id = 4
-- where id in (508,510, 512);

-- update transact
-- set transfer_id = 511
-- where id = 464;

-- update transact
-- set transfer_id = 464
-- where id = 511;

-- update transact
-- set transfer_id = 406
-- where id = 464;

-- update transact
-- set transfer_id = 488,
--    budget_id = ''
-- where id = 480;

-- update transact
-- set transfer_id = 480
-- where id = 488;

-- update transact 
-- set amount = amount - 0.35
-- where id = 497;

select *
from transact
where (
   is_transfer = 1 and transfer_id is null
) or (
   is_transfer = 0 and -1 in (budget_id, income_id)
);

select a.id, name, sum(case when debit_or_credit = '-' then -amount else amount end) as balance
from transact t
left join account a on t.account_id = a.id
group by name;

select sum(amount)
from transact
where account_id = 6 and debit_or_credit = '-';

select sum(amount)
from transact
where account_id = 6 and debit_or_credit = '+';

select sum(case when debit_or_credit = '-' then -amount else amount end) as balance
from transact;

select * from transact;
