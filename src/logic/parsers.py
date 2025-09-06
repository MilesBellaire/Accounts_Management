import sys
sys.path.append('./')

import PyPDF2
import re
import pandas as pd
from database.io.dbio import sql
from inputs import inputs

def parse(filename):
   text = ""

   with open(f"./../data/Statements/{filename}.pdf", "rb") as file:
      reader = PyPDF2.PdfReader(file)

      for page in reader.pages:
         text += page.extract_text().lower()
   # print(filename, text)

   if 'credit card' in text:
      return creditcard_statement(filename, text)
   else:
      return personal_statement(filename, text)

def personal_statement(filename:str, text:str):

   regex = r"^\w\w\w *\d\d? *[^\n]+(?![-+] *\$[\d,\.]+ *\$[\d,\.]+\n)"
   re.sub(r"^(\w\w\w *\d\d? *[^\n]+(?![-+] *\$[\d,\.]+ *\$[\d,\.]+\n))\n", "$1", text)
   # print(text)

   # count = 0
   dates_through = re.search(r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec) *\d\d?) *- *((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec) *\d\d?), *(20\d\d)", text)
   start_date = f"{dates_through.group(1)} {dates_through.group(3)}"
   end_date = f"{dates_through.group(2)} {dates_through.group(3)}"

   if sql.statement.exists(filename) > 0: 
      statement_id = sql.statement.get_id(filename)
      val = inputs.get_yon(f"Statement {filename} already exists. Overwrite?")
      if val == 'y': sql.statement.delete(statement_id)
   statement_id = sql.statement.insert(filename, pd.to_datetime(start_date), pd.to_datetime(end_date))

   # print(start_date, end_date)
   checking = True
   account = ''
   text_split = text.split("\n")
   transactions = pd.DataFrame({
      "Date": [],
      "Description": [],
      "DebitOrCredit": [],
      "Amount": [],
      "NewBalance": [],
      "CheckingOrSavings": [],
      "Account": [],
      "Category": [],
      "AssociatedId": [],
      "IsTransfer": []
   })
      
   for i in range(len(text_split)):
      s = text_split[i]

      if "checking" in s: checking = True
      elif "saving" in s: checking = False

      acc_search = re.search(r"- *(\d{9,})", s)
      if bool(acc_search):
         account = acc_search.group(1)[-4:]
         # print(account)
         continue

      if (
         i < len(text_split)-1 
         and not bool(re.search(r" *[-+] *\$[\d,\.]+ *\$[\d,\.]+$", s))
         and not bool(re.search(r"^\w\w\w *\d\d?", text_split[i+1]))
      ):
         s += " " + text_split[i+1]

      re_out = re.search(r"^(\w\w\w *\d\d?) *(.+) *([-+]) *\$([\d,\.]+) *\$([\d,\.]+)", s)
      if bool(re_out):
         transactions.loc[len(transactions)] = [str(g) for g in re_out.groups()] + ['c' if checking else 's', account, '', '', False]

   # Check if description contains "mobile pmt" or "withdrawl" or "deposit"
   regex = rf"(?:withdrawal|deposit).*xxxxx(?:{'|'.join(list(transactions['Account'].unique()))})|(?:online |mobile |crcard)pmt"
   print(regex)
   transactions['IsTransfer'] = transactions['Description'].str.contains(regex, na=False, regex=True).map({False: 0, True: 1})
   # Accounts for start year being different that end year
   full_transact_date = [row['Date'] + ' ' + (start_date[-4:] if row['Date'][:4] == start_date[:4] else end_date[-4:])for _, row in transactions.iterrows()]
   # print(full_transact_date)
   transactions['Date'] = pd.to_datetime(full_transact_date, format="%b %d %Y")
   transactions['StatementId'] = statement_id
   transactions['Amount'] = transactions['Amount'].str.replace(',', '').astype(float)

   return transactions

def creditcard_statement(filename:str, text:str):
   # count = 0
   possible_months = r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
   dates_through = re.search(rf"({possible_months} *\d\d?), *(20\d\d) *- *({possible_months} *\d\d?), *(20\d\d)", text)
   start_date = f"{dates_through.group(1)} {dates_through.group(2)}"
   end_date = f"{dates_through.group(3)} {dates_through.group(4)}"
   # print(start_date, end_date)

   if sql.statement.exists(filename) > 0: 
      statement_id = sql.statement.get_id(filename)
      val = inputs.get_yon(f"Statement {filename} already exists. Overwrite?")
      if val == 'y': sql.statement.delete(statement_id)
   statement_id = sql.statement.insert(filename, pd.to_datetime(start_date), pd.to_datetime(end_date))

   # print(start_date, end_date)
   checking = True
   account = ''
   text_split = text.split("\n")
   transactions = pd.DataFrame({
      "Date": [],
      "PostDate": [],
      "Description": [],
      "DebitOrCredit": [],
      "Amount": [],
      "CheckingOrSavings": [],
      "Account": [],
      "Category": [],
      "AssociatedId": [],
      "IsTransfer": []
   })
      
   for i in range(len(text_split)):
      s = text_split[i]

      if "checking" in s: checking = True
      elif "saving" in s: checking = False

      acc_search = re.search(r"#(\d{4}):", s)
      if bool(acc_search):
         account = acc_search.group(1)
         # print(account)
         continue

      # if (
      #    i < len(text_split)-1 
      #    and not bool(re.search(r" *[-+] *\$[\d,\.]+ *\$[\d,\.]+$", s))
      #    and not bool(re.search(r"^\w\w\w *\d\d?", text_split[i+1]))
      # ):
      #    s += " " + text_split[i+1]

      re_out = re.search(r"^(\w\w\w *\d\d?) *(\w\w\w *\d\d?) *(.+?) *(-)? *\$([\d,\.]+) *", s)
      if bool(re_out):
         print(s)
         transactions.loc[len(transactions)] = [str(g).strip() for g in re_out.groups()] + ['c' if checking else 's', account, '', '', False]


   # Check if description contains "mobile pmt" or "withdrawl" or "deposit"
   regex = rf"(?:mobile|online|autopay) pymt"
   transactions['IsTransfer'] = transactions['Description'].str.contains(regex, na=False, regex=True).map({False: 0, True: 1})
   # Accounts for start year being different that end year
   # print(full_transact_date)
   transactions['DebitOrCredit'] = transactions['DebitOrCredit'].map({'None': '-', '-': '+'})
   transactions.loc[transactions['DebitOrCredit'] == '+', "Date"] = transactions.loc[transactions['DebitOrCredit'] == '+', "PostDate"]

   full_transact_date = [row['Date'] + ' ' + (start_date[-4:] if row['Date'][:4] == start_date[:4] else end_date[-4:])for _, row in transactions.iterrows()]
   transactions['Date'] = pd.to_datetime(full_transact_date, format="%b %d %Y")
   transactions['StatementId'] = statement_id
   transactions['Amount'] = transactions['Amount'].str.replace(',', '').astype(float)
   transactions = transactions.drop(columns=['PostDate'])
   # print(transactions)
   # exit()
   return transactions

