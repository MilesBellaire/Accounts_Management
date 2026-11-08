from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / 'src'

DB_PATH = SRC_ROOT / 'database' / 'db.db'
DATA_DIR = PROJECT_ROOT / 'data'
STATEMENTS_DIR = DATA_DIR / 'Statements'
