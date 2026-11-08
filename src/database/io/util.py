import pandas as pd


def nullable(value):
	"""Normalize empty strings, NaN and numpy scalars into values sqlite3 can bind.

	Note that float('nan') is truthy, so a plain `x if x else None` lets NaN through.
	"""
	if value is None:
		return None
	if isinstance(value, str):
		return value or None
	try:
		if pd.isna(value):
			return None
	except (TypeError, ValueError):
		return value
	if hasattr(value, 'item'):
		return value.item()
	return value
