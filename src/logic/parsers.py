"""Statement PDF parsing.

Parsing is pure: it reads a PDF and returns the transactions it found. Deciding whether to
overwrite an existing statement, inserting the statement row and staging the transactions
are all the caller's job.
"""

from dataclasses import dataclass, field

import PyPDF2
import pandas as pd
import re

import config

MONTHS = r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'

# The trailing five are filled in after the regex groups: see the row appends below.
PERSONAL_COLUMNS = [
	'Date', 'Description', 'DebitOrCredit', 'Amount', 'NewBalance',
	'CheckingOrSavings', 'Account', 'Category', 'AssociatedId', 'IsTransfer',
]

CREDITCARD_COLUMNS = [
	'Date', 'PostDate', 'Description', 'DebitOrCredit', 'Amount',
	'CheckingOrSavings', 'Account', 'Category', 'AssociatedId', 'IsTransfer',
]


class ParseError(ValueError):
	pass


@dataclass
class ParsedStatement:
	name: str
	kind: str
	start_date: pd.Timestamp
	end_date: pd.Timestamp
	transactions: pd.DataFrame = field(repr=False)


def statement_path(name: str):
	return config.STATEMENTS_DIR / f'{name}.pdf'


def extract_text(path) -> str:
	text = ''
	with open(path, 'rb') as file:
		reader = PyPDF2.PdfReader(file)
		for page in reader.pages:
			text += page.extract_text().lower()
	return text


def parse_statement_file(path, name=None) -> ParsedStatement:
	path = config.STATEMENTS_DIR / f'{path}.pdf' if isinstance(path, str) else path
	return parse_statement_text(extract_text(path), name or path.stem)


def parse_statement_text(text: str, name: str) -> ParsedStatement:
	if 'credit card' in text:
		return creditcard_statement(name, text)
	return personal_statement(name, text)


def parse_with_fallback(date_str, year):
	"""Statement dates occasionally run into the next token; drop trailing characters until
	the date parses."""
	try:
		return pd.to_datetime(date_str + ' ' + year, format='%b %d %Y')
	except ValueError:
		while len(date_str) > 3:
			date_str = date_str[:-1]
			try:
				return pd.to_datetime(date_str + ' ' + year, format='%b %d %Y')
			except ValueError:
				continue
		raise


def _empty_transactions(columns):
	return pd.DataFrame({column: [] for column in columns})


def personal_statement(name: str, text: str) -> ParsedStatement:
	dates_through = re.search(
		rf'({MONTHS} *\d\d?) *- *({MONTHS} *\d\d?), *(20\d\d)', text
	)
	if not dates_through:
		raise ParseError(f'Could not find a statement period in "{name}"')

	start_date = f'{dates_through.group(1)} {dates_through.group(3)}'
	end_date = f'{dates_through.group(2)} {dates_through.group(3)}'

	checking = True
	account = ''
	text_split = text.split('\n')
	transactions = _empty_transactions(PERSONAL_COLUMNS)

	for i in range(len(text_split)):
		s = text_split[i]

		if 'checking' in s:
			checking = True
		elif 'saving' in s:
			checking = False

		acc_search = re.search(r'- *(\d{9,})', s)
		if acc_search:
			account = acc_search.group(1)[-4:]
			continue

		# A transaction description can wrap onto the following line.
		if (
			i < len(text_split) - 1
			and not re.search(r' *[-+] *\$[\d,\.]+ *\$[\d,\.]+$', s)
			and not re.search(r'^\w\w\w *\d\d?', text_split[i + 1])
		):
			s += ' ' + text_split[i + 1]

		re_out = re.search(r'^(\w\w\w *\d\d?) *(.+) *([-+]) *\$([\d,\.]+) *\$([\d,\.]+)', s)
		if re_out:
			# groups: date, description, +/-, amount, new balance
			transactions.loc[len(transactions)] = [str(g) for g in re_out.groups()] + [
				'c' if checking else 's', account, '', '', False
			]

	if transactions.empty:
		raise ParseError(f'No transactions found in "{name}"')

	# Transfers between the user's own accounts, which must not count as income or spending.
	accounts = '|'.join(transactions['Account'].unique())
	transfer_regex = (
		rf'(?:withdrawal|deposit).*xxxxx(?:{accounts})|(?:online |mobile |crcard)pmt'
	)
	transactions['IsTransfer'] = (
		transactions['Description']
		.str.contains(transfer_regex, na=False, regex=True)
		.map({False: 0, True: 1})
	)

	transactions['Date'] = pd.to_datetime([
		parse_with_fallback(
			row['Date'], start_date[-4:] if row['Date'][:4] == start_date[:4] else end_date[-4:]
		)
		for _, row in transactions.iterrows()
	])
	transactions['Amount'] = transactions['Amount'].str.replace(',', '').astype(float)

	return ParsedStatement(
		name=name,
		kind='personal',
		start_date=pd.to_datetime(start_date),
		end_date=pd.to_datetime(end_date),
		transactions=transactions,
	)


def creditcard_statement(name: str, text: str) -> ParsedStatement:
	dates_through = re.search(
		rf'({MONTHS} *\d\d?), *(20\d\d) *- *({MONTHS} *\d\d?), *(20\d\d)', text
	)
	if not dates_through:
		raise ParseError(f'Could not find a statement period in "{name}"')

	start_date = f'{dates_through.group(1)} {dates_through.group(2)}'
	end_date = f'{dates_through.group(3)} {dates_through.group(4)}'

	checking = True
	account = ''
	text_split = text.split('\n')
	transactions = _empty_transactions(CREDITCARD_COLUMNS)

	for s in text_split:
		if 'checking' in s:
			checking = True
		elif 'saving' in s:
			checking = False

		acc_search = re.search(r'#(\d{4}):', s)
		if acc_search:
			account = acc_search.group(1)
			continue

		re_out = re.search(r'^(\w\w\w *\d\d?) *(\w\w\w *\d\d?) *(.+?) *(-)? *\$([\d,\.]+) *', s)
		if re_out:
			# groups: transaction date, post date, description, minus sign or None, amount
			transactions.loc[len(transactions)] = [str(g).strip() for g in re_out.groups()] + [
				'c' if checking else 's', account, '', '', False
			]

	if transactions.empty:
		raise ParseError(f'No transactions found in "{name}"')

	transactions['IsTransfer'] = (
		transactions['Description']
		.str.contains(r'(?:mobile|online|autopay) pymt', na=False, regex=True)
		.map({False: 0, True: 1})
	)

	# On a card statement an amount with no minus sign is a charge; a minus sign is a payment.
	transactions['DebitOrCredit'] = transactions['DebitOrCredit'].map({'None': '-', '-': '+'})
	# Payments are recorded on their post date.
	transactions.loc[transactions['DebitOrCredit'] == '+', 'Date'] = transactions.loc[
		transactions['DebitOrCredit'] == '+', 'PostDate'
	]

	transactions['Date'] = pd.to_datetime([
		row['Date'] + ' ' + (start_date[-4:] if row['Date'][:4] == start_date[:4] else end_date[-4:])
		for _, row in transactions.iterrows()
	], format='%b %d %Y')
	transactions['Amount'] = transactions['Amount'].str.replace(',', '').astype(float)
	transactions = transactions.drop(columns=['PostDate'])

	return ParsedStatement(
		name=name,
		kind='credit card',
		start_date=pd.to_datetime(start_date),
		end_date=pd.to_datetime(end_date),
		transactions=transactions,
	)
