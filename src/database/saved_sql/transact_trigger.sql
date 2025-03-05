-- select * from transact;

drop trigger if exists update_transact_distribution;
drop trigger if exists insert_transact_distribution;

create trigger update_transact_distribution 
after update of income_id on transact
begin 

   insert into distribution(name, income_id, original_id)
   select distinct (datetime('now') || ' ' || d.id || ' ' || d.name || ' clone'), d.income_id, d.id
   from distribution d
   join income i on d.id = i.primary_distribution_id
   join transact t on i.id = t.income_id
   where t.distribution_id is null and t.id = new.id;

   update transact
   set distribution_id = (
      select d2.id
      from transact t
      join income i on t.income_id = i.id
      join distribution d1 on i.id = d1.income_id
      join distribution d2 on d1.id = d2.original_id
      where transact.id = t.id
      order by d2.id desc
      limit 1
   )
   where distribution_id is null and id = new.id;

   insert into distribution_budget(distribution_id, weight, budget_id)
   select distinct d.id, db.weight, db.budget_id
   from transact t
   join distribution d on t.distribution_id = d.id
   join distribution od on d.original_id = od.id
   join distribution_budget db on od.id = db.distribution_id
   where t.id = new.id;

   delete from distribution_budget
   where distribution_id in (
      select id 
      from distribution
      where original_id is not null and id = old.distribution_id
         and income_id = old.income_id
   );

   delete from distribution
   where original_id is not null and id = old.distribution_id
      and income_id = old.income_id;

end;


create trigger insert_transact_distribution after
insert on transact when new.income_id is not null
begin 
   -- select * from transact where new.id = id;

   insert into distribution(name, income_id, original_id)
   select distinct (datetime('now') || ' ' || d.id || ' ' || d.name || ' clone'), d.income_id, d.id
   from distribution d
   join income i on d.id = i.primary_distribution_id
   join transact t on i.id = t.income_id
   where t.distribution_id is null and t.id = new.id;

   update transact
   set distribution_id = (
      select d2.id
      from transact t
      join income i on t.income_id = i.id
      join distribution d1 on i.id = d1.income_id
      join distribution d2 on d1.id = d2.original_id
      where transact.id = t.id
      order by d2.id desc
      limit 1
   )
   where distribution_id is null and id = new.id;

   insert into distribution_budget(distribution_id, weight, budget_id)
   select distinct d.id, db.weight, db.budget_id
   from transact t
   join distribution d on t.distribution_id = d.id
   join distribution od on d.original_id = od.id
   join distribution_budget db on od.id = db.distribution_id
   where t.id = new.id;

end;

-- update transact
-- set income_id = income_id;

insert into transact(income_id)
values (1);

insert into transact(budget_id)
values (1);

delete from distribution_budget
where distribution_id in (
   select id 
   from distribution
   where original_id is not null
)
returning *;

delete from distribution
where original_id is not null
returning *;

select * from transact;

update transact
set distribution_id = null;

delete from transact
where date is null and insert_date is null;