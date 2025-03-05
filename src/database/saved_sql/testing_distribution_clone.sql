
create temporary table temp_map as
   select t.id as transaction_id, d.*
   from distribution d
   join income i on d.id = i.primary_distribution_id
   join transact t on i.id = t.income_id
   where t.distribution_id is null;

select * from temp_map;

insert into distribution(name, income_id, original_id)
select distinct (datetime('now') || ' ' || id || ' ' || name || ' clone'), income_id, id
from temp_map;

select t.id, t.distribution_id, m.id, m.name, d.id, d.name, d.original_id 
-- update t 
-- set distribution_id = m.id
from transact t
join temp_map m on t.id = m.transaction_id
join distribution d on d.original_id = m.id
order by d.id desc
limit (select count(*) from temp_map);


update transact
set distribution_id = (
   select d.id
   from transact t
   join temp_map m on t.id = m.transaction_id
   join distribution d on d.original_id = m.id
   where transact.id = t.id
   order by d.id desc
   limit 1
);

select t.*
from transact t
join temp_map m on t.id = m.transaction_id;

-- select distinct d.id, d.name, od.id, od.name, db.id, db.weight, db.budget_id
insert into distribution_budget(distribution_id, weight, budget_id)
select distinct d.id, db.weight, db.budget_id
from transact t
join distribution d on t.distribution_id = d.id
join distribution od on d.original_id = od.id
join distribution_budget db on od.id = db.distribution_id;

select *
from distribution_budget
where distribution_id in (
   select id 
   from distribution
   where original_id is not null
);

-- delete from distribution_budget
-- where distribution_id in (
--    select id 
--    from distribution
--    where original_id is not null
-- );

-- delete from distribution
-- where original_id is not null;

-- update transact
-- set distribution_id = null;
