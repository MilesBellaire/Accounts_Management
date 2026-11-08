import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / 'src'
WEB_ROOT = PROJECT_ROOT / 'web'

# `streamlit run` puts the main script's folder on sys.path (streamlit.web.bootstrap
# ._fix_sys_path); AppTest does not, so the page smoke tests need it added here.
for path in (SRC_ROOT, WEB_ROOT):
	if str(path) not in sys.path:
		sys.path.insert(0, str(path))


@pytest.fixture(autouse=True, scope='session')
def real_database_is_read_only():
	"""Nothing in the suite may write to the real db.db.

	Page tests exercise the live database, and a stray button press or an unguarded
	module-level call would otherwise edit real financial data. query_only makes any write
	on the shared connection fail loudly instead. Tests that need to exercise writes take a
	disposable copy - see test_staging.py.
	"""
	from database.io.dbio import sql

	sql._conn.execute('PRAGMA query_only = ON;')
	yield
	sql._conn.execute('PRAGMA query_only = OFF;')
