"""Pushing the LP's income -> budget allocation back into distribution_budget.

Every transaction carries a distribution_id; the weights on that distribution are what split
an income across budgets. This recalculates the primary distribution for each income from
the current ideal-budget model, and must succeed before new transactions are staged.
"""

from dataclasses import dataclass, field

import pandas as pd

from database.io.dbio import sql
from logic.shared_logic import generate_accounts_df


@dataclass
class WeightUpdate:
	ok: bool
	message: str = ''
	# The per-income weight sums when they fail to add up to 1.0.
	sums: pd.DataFrame = field(default=None, repr=False)
	distribution: pd.DataFrame = field(default=None, repr=False)


def update_budget_distribution_weights() -> WeightUpdate:
	staged_income = sql.get_transactions_by_income()
	distribution, _ = generate_accounts_df(False)
	distribution = distribution[distribution['Category'] != 'income']

	income_id_by_name = dict(zip(staged_income['name'], staged_income['id']))

	weight_columns = [c for c in distribution.columns if c.endswith(' %')]
	distribution = distribution[['id', 'Name'] + weight_columns]

	sums = distribution[weight_columns].sum().round(2)
	if any(sums != 1.00):
		off = sums[sums != 1.00]
		return WeightUpdate(
			ok=False,
			message=(
				'Budget weights do not add up to 100% for: '
				+ ', '.join(f'{name[:-2]} ({value:.0%})' for name, value in off.items())
			),
			sums=sums.rename('weight').to_frame(),
			distribution=distribution,
		)

	for _, row in distribution.iterrows():
		if row['Name'] in ('Leftover', 'unassigned'):
			continue

		for column in weight_columns:
			income_name = column[:-2]
			if income_name not in income_id_by_name:
				continue
			sql.update_distribution_weight(income_id_by_name[income_name], row['id'], row[column])

	return WeightUpdate(ok=True, distribution=distribution)
