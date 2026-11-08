"""The ideal-budget model.

generate_accounts_df turns the configured incomes and budgets into a per-month plan, and
determine_budget_allocations then solves an LP that decides which income funds which budget,
subject to the income -> budget links stored in distribution_budget.
"""

import pandas as pd
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, PULP_CBC_CMD

from database.io.dbio import sql
from logic.equations import evaluate as Evaluate_equation

# Budgets that are withheld from salary rather than spent. The take-home views fold these
# out of the income instead of showing them as budgets.
EXTERNAL_BUDGETS = ('taxes', '401k')


def get_dollars_per(per_month):
	return [
		'${:,.2f}'.format(per_month / 30.437),
		'${:,.2f}'.format(per_month / 4.345),
		'${:,.2f}'.format(per_month),
		'${:,.2f}'.format(per_month * 12),
		'${:,.2f}'.format(per_month * 60),
	]


def generate_accounts_df(include_external=True):
	incomes = sql.income.get()
	budgets = sql.budget.get()

	# Drop 'other', the catch-all that is not assigned to any budget, and anything bringing in
	# nothing per month.
	incomes = incomes[incomes['name'] != 'other']
	incomes = incomes[incomes['value'] != 0].copy()

	if not include_external:
		# Take-home view: fold tax and 401k out of salary rather than showing them as budgets.
		external = sum(
			budgets[budgets['name'] == name]['value'].iloc[0] for name in EXTERNAL_BUDGETS
		)
		incomes.loc[incomes['name'] == 'salary', 'equation'] += f' * (100-{external})/100'
		budgets = budgets[~budgets['name'].isin(EXTERNAL_BUDGETS)]

	columns = ['Name', 'Percentage', 'Per Month', 'Category', 'id']

	income_per_month = sum(incomes[incomes['unit'] == '$']['value'])
	income_per_month += sum(
		Evaluate_equation(str(income['equation']), income['value'])
		for _, income in incomes[incomes['unit'] == 'eq'].iterrows()
	)

	expenses_per_month = (
		sum(budgets[budgets['unit'] == '%ov']['value'] / 100 * income_per_month)
		+ sum(
			Evaluate_equation(str(budget['equation']), budget['value'])
			for _, budget in budgets[budgets['unit'] == 'eq'].iterrows()
		)
		+ sum(budgets[budgets['unit'] == '$']['value'])
	)

	leftover = income_per_month - expenses_per_month

	percent_cut_by_cap = 0

	# Incomes
	accounts = [
		[income['name'], income['value'] / income_per_month, income['value'], 'income', income['id']]
		for _, income in incomes[incomes['unit'] == '$'].iterrows()
	]

	for _, income in incomes[incomes['unit'] == 'eq'].iterrows():
		amount = Evaluate_equation(str(income['equation']), income['value'])
		accounts.append([
			income['name'],
			amount / income_per_month,
			amount,
			'income',
			income['id'],
		])

	# Percentages of overall income
	accounts += [
		[
			budget['name'],
			budget['value'] / 100,
			budget['value'] / 100 * income_per_month,
			budget['tags'],
			budget['id'],
		]
		for _, budget in budgets[budgets['unit'] == '%ov'].iterrows()
	]

	# Flat dollar amounts
	accounts += [
		[
			budget['name'],
			budget['value'] / income_per_month,
			budget['value'],
			budget['tags'],
			budget['id'],
		]
		for _, budget in budgets[budgets['unit'] == '$'].iterrows()
	]

	# Equation-driven amounts
	for _, budget in budgets[budgets['unit'] == 'eq'].iterrows():
		expense = Evaluate_equation(budget['equation'], budget['value'])
		accounts.append([
			budget['name'],
			expense / income_per_month,
			expense,
			budget['tags'],
			budget['id'],
		])

	# Percentages of leftover, capped
	for _, budget in budgets[budgets['unit'] == '%lo-'].iterrows():
		expense = max(min(budget['value'] / 100 * leftover, budget['cap']), 0)
		accounts.append([
			budget['name'],
			expense / income_per_month,
			expense,
			budget['tags'],
			budget['id'],
		])

		percent_cut_by_cap += max((budget['value'] / 100 - expense / leftover), 0)

	# Percentages of leftover that absorb what the capped ones gave up
	uncapped = budgets[budgets['unit'] == '%lo+']
	for _, budget in uncapped.iterrows():
		additional_percentage = percent_cut_by_cap / len(uncapped)
		leftover_percentage = budget['value'] / 100 + additional_percentage
		percentage = leftover_percentage * leftover / income_per_month

		accounts.append([
			budget['name'],
			percentage,
			percentage * income_per_month,
			budget['tags'],
			budget['id'],
		])

	# Whatever remains
	overall_leftover_percentage = 1 - sum(
		account[1] for account in accounts if account[3] != 'income'
	)
	accounts.append([
		'Leftover',
		overall_leftover_percentage,
		max(overall_leftover_percentage * income_per_month, 0),
		'savings',
		None,
	])

	accounts_df = pd.DataFrame(accounts, columns=columns)

	accounts_df['Percentage'] = accounts_df['Percentage'].clip(lower=0)
	accounts_df['Per Month'] = accounts_df['Per Month'].clip(lower=0)

	accounts_df.sort_values(by='Category', inplace=True, ascending=False)

	return determine_budget_allocations(accounts_df, include_external)


def solve_lp(l1, l2, l3):
	problem = LpProblem("MultiDimensional_Variable", LpMinimize)

	x = {(i, j): LpVariable(f"x{i}{j}", lowBound=0) for i in range(len(l1)) for j in range(len(l2))}

	# Each budget must be funded exactly to its target.
	for j in range(len(l2)):
		problem += lpSum(l1[i] * x[i, j] for i in range(len(l1)) if (i, j) in l3) == l2[j]

	# Each income must be fully allocated.
	for i in range(len(l1)):
		problem += lpSum(x[i, j] for j in range(len(l2))) == 1

	# Weighting by index biases the solver toward funding larger budgets from larger incomes,
	# which keeps the allocation stable between runs.
	problem += lpSum(
		x[i, j] * (i + 1) * (j + 1) * l1[i] for i in range(len(l1)) for j in range(len(l2))
	), "Objective"

	problem.solve(PULP_CBC_CMD(msg=False))

	return {var.name: var.varValue for var in problem.variables()}


def determine_budget_allocations(df: pd.DataFrame, include_external=True):
	"""Attach per-income allocation columns ("<income> %", "<income> $") to each budget row.

	Returns (df, warnings) where warnings lists incomes/budgets the LP could not fully match.
	"""
	warnings = []

	income = sql.income.get()
	income = income[income['name'].isin(df[df['Category'] == 'income']['Name'])]

	if not include_external:
		df = df[~df['Name'].isin(EXTERNAL_BUDGETS)]

	# The LP is happier with numbers that are not tiny fractions.
	df = df.copy()
	df['Percentage'] = df['Percentage'] * 1000

	sorted_incomes = df[df['Category'] == 'income'].sort_values(by='Percentage', ascending=False)
	l1 = sorted_incomes['Percentage'].tolist()
	l1_name = sorted_incomes['Name'].tolist()

	sorted_budgets = df[df['Category'] != 'income'].sort_values(by='Percentage', ascending=False)
	# Leftover absorbs the remainder, so it goes last.
	sorted_budgets = pd.concat([
		sorted_budgets[sorted_budgets['Name'] != 'Leftover'],
		sorted_budgets[sorted_budgets['Name'] == 'Leftover'],
	])
	l2 = sorted_budgets['Percentage'].tolist()
	l2_name = sorted_budgets['Name'].tolist()

	l3 = []
	for _, row in income.iterrows():
		for b in row['budgets'].split(', '):
			if b == '' or (not include_external and b in EXTERNAL_BUDGETS):
				continue
			l3 += [(l1_name.index(row['name']), l2_name.index(b))]
		l3 += [(l1_name.index(row['name']), l2_name.index('Leftover'))]

	solution = solve_lp(l1, l2, l3)

	for i in range(len(l1)):
		total = 0
		for j in range(len(l2)):
			total += l1[i] * solution[f"x{i}{j}"]
			df.loc[df['Name'] == l2_name[j], f"{l1_name[i]} %"] = solution[f"x{i}{j}"]
			df.loc[df['Name'] == l2_name[j], f"{l1_name[i]} $"] = (
				solution[f"x{i}{j}"] * df.loc[df['Name'] == l1_name[i], 'Per Month'].iloc[0]
			)
		if round(l1[i] - total, 2) > 0:
			warnings.append(f"{l1_name[i]} is under-allocated by {round(l1[i] - total, 2)}")

	# An income does not fund itself.
	for n1 in l1_name:
		for n2 in l1_name:
			df.loc[df['Name'] == n2, f"{n1} %"] = 0
			df.loc[df['Name'] == n2, f"{n1} $"] = 0

	for j in range(len(l2)):
		total = 0
		for i in range(len(l1)):
			total += l1[i] * solution[f"x{i}{j}"]
			df.loc[df['Name'] == l1_name[i], f"{l1_name[i]} %"] += solution[f"x{i}{j}"]
			df.loc[df['Name'] == l1_name[i], f"{l1_name[i]} $"] += (
				solution[f"x{i}{j}"] * df.loc[df['Name'] == l1_name[i], 'Per Month'].iloc[0]
			)
		if round(l2[j] - total, 2) > 0:
			warnings.append(f"{l2_name[j]} is under-funded by {round(l2[j] - total, 2)}")

	df['Percentage'] = df['Percentage'] / 1000

	return df, warnings
