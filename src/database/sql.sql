


select number, sum(case when debit_or_credit = '-' then -amount else amount end) as balance
from transact
join account on transact.account_id = account.id
where date < (
   select ifnull(min(date), datetime('now')) from transact
   where (
      is_transfer = 1 and transfer_id is null
   ) or (
      is_transfer = 0 and -1 in (budget_id, income_id)
   )
)
group by number;

select statement_id, count(*) from transact group by statement_id;

select * from transact
where date < (
   select min(date) from transact
   where (
      is_transfer = 1 and transfer_id is null
   ) or (
      is_transfer = 0 and -1 in (budget_id, income_id)
   )
)
order by date;

select * from transact
where (
   is_transfer = 1 and transfer_id is null
) or (
   is_transfer = 0 and -1 in (budget_id, income_id)
);

select * from account;

-- select *
-- from transact
-- where date < (
--    select min(date) from transact
--    where (
--       is_transfer = 1 and transfer_id is null
--    ) or (
--       is_transfer = 0 and -1 in (budget_id, income_id)
--    )
-- );


-- select * from transact
-- where (
--    is_transfer = 1 and transfer_id is null
-- ) or (
--    is_transfer = 0 and -1 in (budget_id, income_id)
-- )
-- order by date;


-- select * from budget;

SELECT name, type, sql 
FROM sqlite_master 
WHERE type IN ('table', 'view') 
ORDER BY name;

