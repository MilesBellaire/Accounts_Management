import pytest

from logic.equations import EquationError, evaluate_arithmetic


@pytest.mark.parametrize(
	'expression, expected',
	[
		('2 + 3', 5),
		('2 + 3 * 4', 14),
		('(2 + 3) * 4', 20),
		('10 / 4', 2.5),
		('-5 + 2', -3),
		('100 * (100-22.5)/100', 77.5),
	],
)
def test_arithmetic(expression, expected):
	assert evaluate_arithmetic(expression) == pytest.approx(expected)


@pytest.mark.parametrize(
	'expression',
	[
		'__import__("os").system("echo pwned")',
		'open("/etc/passwd").read()',
		'[].__class__',
		'2 ** 64',
		'exec("x=1")',
		'lambda: 1',
		'x + 1',
		'',
	],
)
def test_rejects_non_arithmetic(expression):
	with pytest.raises(EquationError):
		evaluate_arithmetic(expression)


def test_rejects_division_by_zero():
	with pytest.raises(EquationError):
		evaluate_arithmetic('5 / 0')


def test_rejects_booleans():
	with pytest.raises(EquationError):
		evaluate_arithmetic('True')
