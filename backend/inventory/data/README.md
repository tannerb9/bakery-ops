# Reference data

`reference_densities.csv`: default densities for common ingredients, suggested when a bakery
adds an ingredient. Bakeries can always override them.

- **Source:** King Arthur Baking ingredient weight chart,
  https://www.kingarthurbaking.com/learn/ingredient-weight-chart (accessed 2026-10-26).
  Rows store the chart's measure (`grams` per `quantity` `unit`); density is derived at load time
  to 6 decimal places.
- **Exception:** water uses its real density (1.0 g/ml), not the chart's 8 oz shortcut (decision D60).
- `tests/test_units.py` checks that every row converts back to the chart's grams.
