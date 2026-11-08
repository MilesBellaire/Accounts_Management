"""Evaluation of the user-authored budget/income equations.

An equation looks like `[self] * 2 + [gas] * [commute_miles]`: bracketed names are
substituted with the value of the matching constant, income or budget (recursively, since
those may carry equations of their own), and the resulting arithmetic is evaluated.

Substitution produces an arithmetic string, which is then evaluated through a whitelisted
AST walk rather than eval() - these equations are editable from the browser.
"""

import ast
import operator
import re

from database.io.dbio import sql


class EquationError(ValueError):
	pass


_BINARY_OPS = {
	ast.Add: operator.add,
	ast.Sub: operator.sub,
	ast.Mult: operator.mul,
	ast.Div: operator.truediv,
}

_UNARY_OPS = {
	ast.UAdd: operator.pos,
	ast.USub: operator.neg,
}


def evaluate_arithmetic(expression: str) -> float:
	"""Evaluate a pure-arithmetic string. Anything but + - * / and numbers is rejected."""
	if not expression.strip():
		raise EquationError('Equation is empty')

	try:
		tree = ast.parse(expression, mode='eval')
	except SyntaxError as exc:
		raise EquationError(f'Could not parse "{expression}": {exc.msg}') from exc

	return _eval_node(tree.body, expression)


def _eval_node(node, expression):
	if isinstance(node, ast.Constant):
		if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
			raise EquationError(f'"{node.value!r}" is not a number')
		return float(node.value)

	if isinstance(node, ast.BinOp):
		op = _BINARY_OPS.get(type(node.op))
		if op is None:
			raise EquationError(f'Operator not allowed in "{expression}" (use + - * /)')
		right = _eval_node(node.right, expression)
		if op is operator.truediv and right == 0:
			raise EquationError(f'Division by zero in "{expression}"')
		return op(_eval_node(node.left, expression), right)

	if isinstance(node, ast.UnaryOp):
		op = _UNARY_OPS.get(type(node.op))
		if op is None:
			raise EquationError(f'Operator not allowed in "{expression}" (use + - * /)')
		return op(_eval_node(node.operand, expression))

	raise EquationError(f'"{expression}" contains something other than arithmetic')


def evaluate(equation, base: float, incomes_used=None, budgets_used=None) -> float:
	"""Resolve the bracketed names in `equation` and evaluate the result.

	`base` is what [self] resolves to. incomes_used/budgets_used guard against an equation
	referring back to something already being resolved further up the recursion.
	"""
	incomes_used = list(incomes_used or [])
	budgets_used = list(budgets_used or [])

	if equation in ('null', None, 'nan', ''):
		return base

	constants = sql.get_constants()
	incomes = sql.income.get()
	incomes = incomes[(incomes['unit'] == '$') | (incomes['unit'] == 'eq')]
	budgets = sql.budget.get()
	budgets = budgets[(budgets['unit'] == '$') | (budgets['unit'] == 'eq')]

	split_equation = re.split(r'[\[\]]', str(equation).replace(' ', ''))

	new_incomes_used = [
		incomes[incomes['name'] == split]['id'].iloc[0]
		for split in split_equation
		if len(incomes[incomes['name'] == split]['id'])
	] + incomes_used
	new_budgets_used = [
		budgets[budgets['name'] == split]['id'].iloc[0]
		for split in split_equation
		if len(budgets[budgets['name'] == split]['id'])
	] + budgets_used

	filled_equation = ''
	for split in split_equation:
		if split == 'self':
			filled_equation += str(base)
		elif split in constants['name'].tolist():
			filled_equation += str(constants[constants['name'] == split]['value'].iloc[0])
		elif split in incomes['name'].tolist():
			row = incomes[incomes['name'] == split].iloc[0]
			if row['id'] in incomes_used:
				continue
			filled_equation += str(
				evaluate(row['equation'], row['value'], new_incomes_used, new_budgets_used)
			)
		elif split in budgets['name'].tolist():
			row = budgets[budgets['name'] == split].iloc[0]
			if row['id'] in budgets_used:
				continue
			filled_equation += str(
				evaluate(row['equation'], row['value'], new_incomes_used, new_budgets_used)
			)
		else:
			filled_equation += split

	return evaluate_arithmetic(filled_equation)


def available_variables():
	"""Names an equation may reference, for display next to an equation input."""
	constants = sql.get_constants()['name'].tolist()

	incomes = sql.income.get()
	incomes = incomes[(incomes['unit'] == '$') | (incomes['unit'] == 'eq')]['name'].tolist()

	budgets = sql.budget.get()
	budgets = budgets[(budgets['unit'] == '$') | (budgets['unit'] == 'eq')]['name'].tolist()

	return constants + incomes + budgets


def validate(equation: str):
	"""Check an equation the user just typed. Returns an error string, or None if it is fine.

	Requires [self], mirroring what the old CLI equation prompt enforced.
	"""
	if not equation or not equation.strip():
		return 'Equation is empty'

	names = re.findall(r'\[([^\]]*)\]', equation)
	if 'self' not in names:
		return 'Equation must reference [self]'

	known = set(available_variables()) | {'self'}
	unknown = [name for name in names if name not in known]
	if unknown:
		return f'Unknown variable(s): {", ".join(sorted(set(unknown)))}'

	try:
		evaluate(equation, 0)
	except EquationError as exc:
		return str(exc)
	except Exception as exc:  # a bad reference can surface as an index/type error
		return f'Could not evaluate equation: {exc}'

	return None
