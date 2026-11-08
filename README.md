# Accounts Management

Personal budgeting: statement PDFs are parsed into transactions, each one is assigned a
budget (spending) or an income, and a linear program splits every income across budgets to
produce per-budget balances.

## Running

```bash
.venv/bin/python -m streamlit run web/app.py
```

Then open http://localhost:8501.

## Tests

```bash
.venv/bin/python -m pytest
```

The suite opens the real `db.db` with `PRAGMA query_only = ON` (see `tests/conftest.py`), so
any write to it fails loudly rather than editing real data. Tests that need to exercise
writes — staging, the CRUD paths, the triggers — copy the database to a temp file first and
work on that. See `tests/test_staging.py`.

## Layout

```
web/                    Streamlit UI
  app.py                Dashboard (entry point)
  bootstrap.py          Import path, the period picker, cached reads, cache invalidation
  format.py             Money/percent formatting and chart styling
  pages/                One file per page
src/
  config.py             Paths, resolved from the repo root
  database/
    db.db               SQLite database
    io/                 One module per table; the only place SQL is written
    saved_sql/          Schema and view definitions, kept for reference
  logic/
    parsers.py          Statement PDF -> transactions (pure)
    categorize.py       Keyword matching -> budget/income suggestions
    equations.py        The [self] + [var] equation language
    shared_logic.py     The ideal-budget model and its LP
    plan.py             Ideal-budget views
    reports.py          Actual balances over a period
    variance.py         Planned spending against actual spending
    timeseries.py       Month-by-month spending, income and balances
    transfers.py        Moving money between budget balances
    distribution_weights.py   Pushing the LP result into distribution_budget
tests/
data/Statements/        Statement PDFs (gitignored)
```

## Concepts

**Budget** — a spending bucket. Its `unit` decides how its target is computed:

| Unit | Meaning |
| --- | --- |
| `$` | A flat amount per month |
| `%ov` | A percentage of overall income |
| `%lo-` | A percentage of what is left after fixed expenses, capped |
| `%lo+` | A percentage of what is left, absorbing what the capped ones give up |
| `eq` | An amount computed from an equation |

**Income** — money coming in, linked to the budgets it funds. The split is solved by the LP
in `shared_logic.determine_budget_allocations` and stored as weights on the income's
*primary distribution*.

**Distribution** — the weights that split one income across budgets. Every transaction
points at a distribution; database triggers clone the primary distribution onto each new
transaction so that changing the plan later does not retroactively rewrite old balances.

**Equations** — `[self] * 2 + [gas]`. Bracketed names resolve to a constant, income or
budget; `[self]` is the row's own value. Only `+ - * /` are allowed.

**Keywords** — a keyword assigns any transaction whose description contains it to a budget
or income automatically on import.

**Plan vs actual** — the plan is per-month, so a target for a window is the per-month
figure times the length of that window. A window that has not finished also carries
`expected` (the plan up to today) and `projected` (the rate so far, carried to the end), so a
budget that is under for the month but running hot is still visible. Spending against a
budget the plan does not fund comes back as `unplanned` rather than being dropped.

**Over time** — the monthly series are dense: every month in the window appears for every
series, zero-filled, because a gap in a line reads as "no data" rather than "nothing spent"
and a running balance cannot skip a month. Categorical palettes hold eight series, so a
longer list either rolls up to a coarser grouping or folds its tail into one `other`.

**Transfers** — move money between budget balances without inventing a transaction, for
when one bucket has piled up and another has run short.

## Notes

- The database schema is treated as fixed. All SQL lives in `src/database/io/`.
- `data/Statements/` and `db.db` are gitignored.
