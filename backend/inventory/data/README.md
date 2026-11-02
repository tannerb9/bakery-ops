# Reference data

`reference_densities.csv`: default densities for common ingredients, suggested when a bakery
adds an ingredient. Bakeries can always override them.

- **Source:** King Arthur Baking ingredient weight chart,
  https://www.kingarthurbaking.com/learn/ingredient-weight-chart (accessed 2026-10-26).
  Rows store the chart's measure (`grams` per `quantity` `unit`); density is derived at load time
  to 6 decimal places.
- **Exceptions:** liquids where the chart uses the "1 cup = 8 oz" shortcut (227 g) use real weights instead:
  water 1.0 g/ml (D60); milk 244 g, heavy cream 238 g, yogurt 245 g per cup from USDA FoodData Central (D60a).
- `tests/test_units.py` checks that every row converts back to the chart's grams.
