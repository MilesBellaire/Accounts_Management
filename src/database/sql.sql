-- create table balance(
--    id integer primary key AUTOINCREMENT,
--    insert_date text,
--    asof_date text,
--    amount read,
--    budget_id integer,
--    prev_balance_id integer,
--    foreign key budget_id REFERENCES budget(id)
-- );


with final as (
   select *
   from transact
   where date < (
      select min(date) from transact
      where (
         is_transfer = 1 and transfer_id is null
      ) or (
         is_transfer = 0 and -1 in (budget_id, income_id)
      )
   )
   order by date
),
g as (
   select b.account_id, b.name, sum(amount) as total, min(date) as start_date, max(date) as end_date
   from final as f
   join budget as b
   on f.budget_id = b.id
   group by b.name
   --    union 
   -- select i.account_id, i.name, sum(amount)
   -- from final as f
   -- join income as i
   -- on f.income_id = i.id
   -- group by i.name
)
select g.*, a.name
from g
join account as a
on g.account_id = a.id;

select *
from transact
where date < (
   select min(date) from transact
   where (
      is_transfer = 1 and transfer_id is null
   ) or (
      is_transfer = 0 and -1 in (budget_id, income_id)
   )
);


select * from transact
where (
   is_transfer = 1 and transfer_id is null
) or (
   is_transfer = 0 and -1 in (budget_id, income_id)
)
order by date;


-- select * from budget;

SELECT name, type, sql 
FROM sqlite_master 
WHERE type IN ('table', 'view') 
ORDER BY name;

