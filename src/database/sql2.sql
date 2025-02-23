with final as (
				select *
				from transact
				where date < (
					select ifnull(min(date), datetime('now')) as date from transact
					where (
						is_transfer = 1 and transfer_id is null
					) or (
						is_transfer = 0 and -1 in (budget_id, income_id)
					)
				)
				order by date
			),
			g as (
				select b.account_id, b.id, b.name, sum(amount) as total, min(date) as start_date, max(date) as end_date
				from budget as b
				left join final as f
				on f.budget_id = b.id
				group by b.name
			),
			most_recent_balance as (
				select bal.*
				from balance as bal
				left join budget as b
				on bal.budget_id = b.id
				where bal.asof_date = (
					select max(asof_date)
					from balance as bal
					left join budget as b
					on bal.budget_id = b.id
				)
			)
			select a.name as account, ifnull(g.name,'undecided') as name, bal.amount as initial_balance, ifnull(g.total,0.0) as total_debits -- new balance and total_credits added in python
			from most_recent_balance as bal
			left join g
			on bal.budget_id = g.id
			left join account as a
			on g.account_id = a.id
			order by g.name;