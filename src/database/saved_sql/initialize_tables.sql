CREATE TABLE account(
   id integer primary key AUTOINCREMENT,
   number integer,
   name text
);
CREATE TABLE budget (
   id integer primary key AUTOINCREMENT,
   name text,
   equation text,
   tags text,
   tracking_type_id integer,
	unit_id integer,
	value real,
	cap real,
	account_id integer
);
CREATE TABLE "constants" (
"name" TEXT,
  "value" REAL
);
CREATE TABLE income(
   id integer primary key AUTOINCREMENT,
   name text,
   equation text,
   tags text,
   tracking_type_id integer,
	unit_id integer,
	value real
);
CREATE TABLE income_budget(
   id integer primary key AUTOINCREMENT,
   income_id integer,
   budget_id integer,
   foreign key (income_id) REFERENCES Income(id),
   foreign key (budget_id) REFERENCES Budget(id)
);
CREATE TABLE "incomes" (
"name" TEXT,
  "$perhour" REAL,
  "hours" REAL
);
CREATE TABLE keyword(
   text text,
   budget_id integer,
   income_id integer, 
   foreign key (budget_id) references budget(id),
   foreign key (income_id) REFERENCES income(id)
);
CREATE TABLE statement(
   id integer primary key AUTOINCREMENT,
   name text,
   start_date text,
   end_date text
);
CREATE TABLE tracking_type (
   id integer primary key AUTOINCREMENT,
   name text
);
CREATE TABLE transact(
   id integer primary key AUTOINCREMENT,
   date text,
   insert_date text,
   description text,
   debit_or_credit text,
   amount real,
   class text,
   budget_id integer,
   income_id integer,
   is_transfer integer,
   transfer_id integer, 
   statement_id integer,
   balance_id integer,
	account_id integer,
   foreign key (income_id) REFERENCES Income(id),
   foreign key (budget_id) REFERENCES Budget(id),
   foreign key (statement_id) REFERENCES statement(id)
);
CREATE TABLE unit(
   id integer primary key AUTOINCREMENT,
   abv text,
   name text,
   description text
);


create view budget_balance as 
with credits as (
   select a.id as account_id, a.name as account, b.id as budget_id,b.name, round(sum(t.amount * db.weight), 2) as amount
   from transact t
   join income i on t.income_id = i.id
   join distribution d on i.primary_distribution_id = d.id
   join distribution_budget db on d.id = db.distribution_id
   join budget b on db.budget_id = b.id
   join account a on b.account_id = a.id
   where t.debit_or_credit = '+' and is_transfer = 0
   group by a.name, b.id, b.name, a.id
   union all
   select
      2,
      'savings', 
      0, 
      'unassigned', 
   round((
      select sum(amount) 
      from transact 
      where is_transfer = 0 and debit_or_credit = '+'
   ) - sum(t.amount * db.weight), 2)
   from transact t
   join income i on t.income_id = i.id
   join distribution d on i.primary_distribution_id = d.id
   join distribution_budget db on d.id = db.distribution_id
   join budget b on db.budget_id = b.id
),
debits as (
   select b.account_id, b.id, b.name, sum(amount) as total, min(date) as start_date, max(date) as end_date
   from budget as b
   left join transact as f
   on f.budget_id = b.id
   group by b.name
),
transfers as (
   select 1 -- need to implement
)
select 
   credits.account,
   credits.name,
   ifnull(debits.total,0.0) as total_debits,
   credits.amount as total_credits,
   credits.amount - ifnull(debits.total,0.0) as balance,
   credits.account_id,
   credits.budget_id
from credits
left join debits
on credits.budget_id = debits.id
order by credits.account, credits.name;