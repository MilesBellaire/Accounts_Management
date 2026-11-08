"""Moving money between budget balances.

A transfer is a pair of rows in the budget_transact view sourced from
budget_balance_transfer, so balances shift without inventing a transaction.
"""

from database.io.dbio import sql


def budget_balances():
	"""Current balance per budget, for picking a source and destination."""
	return sql.budget_balance.get_all()


def validate_transfer(from_budget_id, to_budget_id, amount, balances=None):
	"""Returns an error message, or None if the transfer is allowed."""
	if amount is None or amount <= 0:
		return 'Amount must be greater than zero'

	if from_budget_id == to_budget_id:
		return 'Source and destination must be different budgets'

	balances = budget_balances() if balances is None else balances
	source = balances[balances['budget_id'] == from_budget_id]

	if source.empty:
		return 'Source budget has no balance to transfer from'

	source_balance = source.iloc[0]['balance']
	if source_balance - amount < 0:
		return (
			f'Transferring ${amount:,.2f} would leave the source budget at '
			f'${source_balance - amount:,.2f}'
		)

	return None


def preview_transfer(from_budget_id, to_budget_id, amount, balances=None):
	"""(source before, source after, destination before, destination after)."""
	balances = budget_balances() if balances is None else balances

	def balance_of(budget_id):
		row = balances[balances['budget_id'] == budget_id]
		return float(row.iloc[0]['balance']) if not row.empty else 0.0

	source = balance_of(from_budget_id)
	destination = balance_of(to_budget_id)

	return source, source - amount, destination, destination + amount


def apply_transfer(from_budget_id, to_budget_id, amount):
	return sql.budget_balance.insert_transfer(int(from_budget_id), int(to_budget_id), float(amount))


def transfer_history():
	return sql.budget_balance.get_transfers()
