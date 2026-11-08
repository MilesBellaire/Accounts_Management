"""Parser tests against synthetic statement text.

The fixtures reproduce the shape the regexes expect (lowercased PDF text, one transaction
per line) rather than any real statement.
"""

import pandas as pd
import pytest

from logic.parsers import ParseError, parse_statement_text

PERSONAL = """
account summary
statement period jan 3 - feb 2, 2025
primary checking - 123456789012
jan 05 grocery mart #221 - $54.30 $1,945.70
jan 09 paycheck deposit + $2,000.00 $3,945.70
jan 14 online pmt to card - $300.00 $3,645.70
savings account - 987654321098
jan 20 transfer withdrawal xxxxx1098 - $100.00 $5,400.00
"""

CREDIT_CARD = """
your credit card statement
billing cycle jan 5, 2025 - feb 4, 2025
account #4321:
jan 07 jan 08 coffee roasters $12.45
jan 19 jan 20 hardware store $87.10
feb 01 feb 02 autopay pymt thank you -$450.00
"""


def test_personal_statement_rows():
	parsed = parse_statement_text(PERSONAL, 'personal-jan')

	assert parsed.kind == 'personal'
	assert parsed.start_date == pd.Timestamp('2025-01-03')
	assert parsed.end_date == pd.Timestamp('2025-02-02')
	assert len(parsed.transactions) == 4


def test_personal_statement_amounts_and_signs():
	parsed = parse_statement_text(PERSONAL, 'personal-jan')
	rows = parsed.transactions.set_index(
		parsed.transactions['Description'].str.split().str[0]
	)

	assert rows.loc['grocery', 'DebitOrCredit'] == '-'
	assert rows.loc['grocery', 'Amount'] == pytest.approx(54.30)
	assert rows.loc['paycheck', 'DebitOrCredit'] == '+'
	assert rows.loc['paycheck', 'Amount'] == pytest.approx(2000.00)


def test_personal_statement_flags_transfers():
	parsed = parse_statement_text(PERSONAL, 'personal-jan')
	transfers = parsed.transactions[parsed.transactions['IsTransfer'] == 1]

	assert len(transfers) == 2
	assert set(transfers['Description'].str.split().str[0]) == {'online', 'transfer'}


def test_personal_statement_splits_accounts():
	parsed = parse_statement_text(PERSONAL, 'personal-jan')

	assert set(parsed.transactions['Account']) == {'9012', '1098'}
	assert set(parsed.transactions['CheckingOrSavings']) == {'c', 's'}


def test_credit_card_statement_rows():
	parsed = parse_statement_text(CREDIT_CARD, 'card-jan')

	assert parsed.kind == 'credit card'
	assert parsed.start_date == pd.Timestamp('2025-01-05')
	assert parsed.end_date == pd.Timestamp('2025-02-04')
	assert len(parsed.transactions) == 3
	assert set(parsed.transactions['Account']) == {'4321'}


def test_credit_card_sign_mapping():
	"""On a card statement a bare amount is a charge; a minus sign is a payment."""
	parsed = parse_statement_text(CREDIT_CARD, 'card-jan')
	rows = parsed.transactions.set_index(
		parsed.transactions['Description'].str.split().str[0]
	)

	assert rows.loc['coffee', 'DebitOrCredit'] == '-'
	assert rows.loc['autopay', 'DebitOrCredit'] == '+'
	assert rows.loc['autopay', 'IsTransfer'] == 1
	assert rows.loc['coffee', 'IsTransfer'] == 0


def test_credit_card_payment_uses_post_date():
	parsed = parse_statement_text(CREDIT_CARD, 'card-jan')
	payment = parsed.transactions[parsed.transactions['DebitOrCredit'] == '+'].iloc[0]

	assert payment['Date'] == pd.Timestamp('2025-02-02')


def test_missing_period_raises():
	with pytest.raises(ParseError):
		parse_statement_text('nothing useful here', 'junk')


def test_no_transactions_raises():
	with pytest.raises(ParseError):
		parse_statement_text('statement period jan 3 - feb 2, 2025\n', 'empty')
