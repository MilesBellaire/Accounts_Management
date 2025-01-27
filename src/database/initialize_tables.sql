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