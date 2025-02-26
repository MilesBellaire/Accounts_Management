

-- update transact
-- set income_id = 1
-- where id = 494;

-- create table distribution(
--    id integer primary key AUTOINCREMENT,
--    name text,
--    income_id int,
--    foreign key (income_id) references income(id) 
-- );

-- create table distribution_budget(
--    id integer primary key AUTOINCREMENT,
--    weight real,
--    distribution_id int,
--    budget_id int,
--    foreign key (distribution_id) REFERENCES distribution(id),
--    foreign key (budget_id) references budget(id)
-- );

-- alter table income
-- add primary_distribution_id int;

-- insert into distribution(name, income_id)
-- select distinct 'primary', income_id
-- from income_budget;

-- insert into distribution_budget(weight, distribution_id, budget_id)
-- select 0.0, d.id, budget_id
-- from income_budget ib
-- join distribution d on ib.income_id = d.income_id;

-- update income as i
-- set primary_distribution_id = (
--    select d.id
--    from distribution d
--    where income_id = i.id
-- );

-- select *
-- from transact
-- where (
--    is_transfer = 1 and transfer_id is null
-- ) or (
--    is_transfer = 0 and -1 in (budget_id, income_id)
-- );

-- select a.id, name, sum(case when debit_or_credit = '-' then -amount else amount end) as balance
-- from transact t
-- left join account a on t.account_id = a.id
-- group by name;

-- select budget.id, budget.name, sum(amount), count(*)
-- from transact
-- left join budget on budget.id = budget_id
-- where debit_or_credit = '-' AND is_transfer = 0
-- group by budget.name, budget.id;

-- select income.id, income.name, sum(amount), count(*)
-- from transact
-- left join income on income.id = income_id
-- where debit_or_credit = '+' AND is_transfer = 0
-- group by income.name, income.id;

-- select sum(amount) as total_debit
-- from transact
-- where debit_or_credit = '-' and is_transfer = 0;

-- select sum(amount) as total_credit
-- from transact
-- where debit_or_credit = '+' and is_transfer = 0;

-- select sum(case when debit_or_credit = '-' then -amount else amount end) as balance
-- from transact;

-- select * from transact
-- left join budget on budget.id = budget_id
-- where budget.id is null and debit_or_credit = '-' and is_transfer = 0;

-- select * from balance;

-- select * from account;

-- select * from transact
-- where income_id = 4;

