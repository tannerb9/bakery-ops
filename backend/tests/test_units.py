"""Unit and density conversion (decisions D16, D18, D19, D59, D60).

Expected values come from King Arthur's ingredient weight chart
(https://www.kingarthurbaking.com/learn/ingredient-weight-chart). Each case converts a
*different* amount than the chart row it's based on, so the unit math is really tested.
Exact-halfway cases (e.g. 2 1/4 tsp yeast = 6.75 g) are avoided on purpose: the chart
itself is rounded, so a halfway result flips on tiny precision differences.
"""

from decimal import Decimal
from fractions import Fraction

import pytest

from inventory.units import (
    ImpreciseMeasureError,
    InvalidQuantityError,
    MissingConversionError,
    UnknownUnitError,
    density_from_measure,
    display_grams,
    load_reference_densities,
    parse_quantity,
    to_grams,
)


def chart(grams: str, quantity: str, unit: str) -> Decimal:
    """Density as it would be stored for a chart row like '1 cup = 120 g'."""
    return density_from_measure(Decimal(grams), quantity, unit)


@pytest.mark.parametrize(
    ("label", "quantity", "unit", "density", "expected"),
    [
        ("3/4 C all-purpose flour", "3/4", "C", chart("120", "1", "cup"), "90"),
        ("1/4 C brown sugar, packed", "1/4", "C", chart("213", "1", "cup"), "53"),
        ("1 tbsp butter", "1", "tbsp", chart("113", "8", "tbsp"), "14"),
        ("1 tsp Diamond Crystal kosher salt", "1", "tsp", chart("8", "1", "tbsp"), "2.7"),
        ("1 tsp Morton kosher salt", "1", "tsp", chart("16", "1", "tbsp"), "5.3"),
        ("1/4 tsp bs", "1/4", "tsp", chart("3", "1/2", "tsp"), "1.5"),
        ("1 1/2 tsp bs (mixed fraction)", "1 1/2", "tsp", chart("3", "1/2", "tsp"), "9.0"),
        ("1 tbsp bp", "1", "tbsp", chart("4", "1", "tsp"), "12"),
        ("1 C cocoa", "1", "C", chart("42", "1/2", "cup"), "84"),
        ("1/4 C honey", "1/4", "C", chart("21", "1", "tbsp"), "84"),
        ("1 C water (real density, not the chart's 227 g)", "1", "C", Decimal("1"), "237"),
    ],
)
def test_volume_to_grams_matches_the_chart(
    label: str, quantity: str, unit: str, density: Decimal, expected: str
) -> None:
    grams = to_grams(quantity, unit, density_g_per_ml=density)

    assert display_grams(grams) == Decimal(expected), label


def test_same_volume_of_two_salt_brands_weighs_about_double() -> None:
    diamond = to_grams("1", "tsp", density_g_per_ml=chart("8", "1", "tbsp"))
    morton = to_grams("1", "tsp", density_g_per_ml=chart("16", "1", "tbsp"))

    assert morton == pytest.approx(diamond * 2, rel=Decimal("0.001"))


def test_eggs_by_count() -> None:
    assert display_grams(to_grams("3", "each", grams_per_each=Decimal("50"))) == Decimal("150")


@pytest.mark.parametrize(
    ("quantity", "unit", "expected"),
    [
        ("4", "oz", "113"),  # matches the chart: 4 oz butter = 113 g
        ("1", "lb", "454"),
        ("1", "kg", "1000"),
        ("500", "g", "500"),
    ],
)
def test_weights_convert_without_any_density(quantity: str, unit: str, expected: str) -> None:
    assert display_grams(to_grams(quantity, unit)) == Decimal(expected)


def test_ounce_and_pound_use_exact_legal_definitions() -> None:
    assert to_grams("1", "oz") == Decimal("28.349523125")
    assert to_grams("1", "lb") == Decimal("453.59237")


def test_cup_tablespoon_teaspoon_ratios_are_exact() -> None:
    # US cup = 236.5882365 ml; 16 tbsp per cup; 3 tsp per tbsp.
    one = Decimal("1")
    assert to_grams("1", "cup", density_g_per_ml=one) == Decimal("236.5882365")
    assert to_grams("16", "tbsp", density_g_per_ml=one) == to_grams(
        "1", "cup", density_g_per_ml=one
    )
    assert to_grams("3", "tsp", density_g_per_ml=one) == to_grams("1", "tbsp", density_g_per_ml=one)


def test_metric_volume_and_fluid_ounce() -> None:
    one = Decimal("1")
    assert to_grams("1", "l", density_g_per_ml=one) == Decimal("1000")
    assert to_grams("250", "ml", density_g_per_ml=one) == Decimal("250")
    assert to_grams("8", "fl oz", density_g_per_ml=one) == to_grams(
        "1", "cup", density_g_per_ml=one
    )


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("C", "cup"),
        ("c", "cup"),
        ("cups", "cup"),
        ("Tbsp", "tbsp"),
        ("tablespoons", "tbsp"),
        ("teaspoon", "tsp"),
        ("grams", "g"),
        ("ML", "ml"),
        ("ea", "each"),
    ],
)
def test_unit_aliases_including_ts_shorthand(alias: str, canonical: str) -> None:
    density = Decimal("0.5")
    assert to_grams("2", alias, density_g_per_ml=density, grams_per_each=Decimal("10")) == to_grams(
        "2", canonical, density_g_per_ml=density, grams_per_each=Decimal("10")
    )


# --- Never guess: these must raise (D19, D59) ---------------------------------------


def test_volume_without_density_raises() -> None:
    with pytest.raises(MissingConversionError):
        to_grams("1", "cup")


def test_count_without_weight_per_item_raises() -> None:
    with pytest.raises(MissingConversionError):
        to_grams("2", "each")


@pytest.mark.parametrize(
    "unit", ["rnd tbsp", "rounded tsp", "heaping cup", "scant cup", "pinch", "dash"]
)
def test_imprecise_measures_raise_instead_of_guessing(unit: str) -> None:
    with pytest.raises(ImpreciseMeasureError):
        to_grams("1", unit, density_g_per_ml=Decimal("1"))


def test_unknown_unit_raises() -> None:
    with pytest.raises(UnknownUnitError):
        to_grams("1", "handful", density_g_per_ml=Decimal("1"))


@pytest.mark.parametrize("bad", ["-1", "abc", "1/0", "", "1 1/2/3"])
def test_bad_quantities_raise(bad: str) -> None:
    with pytest.raises(InvalidQuantityError):
        parse_quantity(bad)


def test_zero_is_allowed() -> None:
    assert to_grams("0", "g") == Decimal("0")


# --- Quantity parsing ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2", Fraction(2)),
        ("1/2", Fraction(1, 2)),
        ("2 1/4", Fraction(9, 4)),
        ("1.5", Fraction(3, 2)),
        (" 3/4 ", Fraction(3, 4)),
    ],
)
def test_parse_quantity(text: str, expected: Fraction) -> None:
    assert parse_quantity(text) == expected


def test_one_third_cup_is_exact_not_rounded_early() -> None:
    # 1/3 cup three times must equal exactly 1 cup — no 0.333 drift.
    one = Decimal("1")
    third = to_grams("1/3", "cup", density_g_per_ml=one)
    assert third * 3 == pytest.approx(
        to_grams("1", "cup", density_g_per_ml=one), abs=Decimal("1e-20")
    )


# --- Display rounding (D60) ------------------------------------------------------------


@pytest.mark.parametrize(
    ("grams", "shown"),
    [
        ("2.66666", "2.7"),  # under 10 g: 0.1 g, like a precision scale
        ("9.94", "9.9"),
        ("9.96", "10"),  # rounds into the whole-gram range
        ("14.1250", "14"),  # 10 g and up: whole grams, like a kitchen scale
        ("236.5882365", "237"),
        ("0.04", "0.0"),
    ],
)
def test_display_rounding(grams: str, shown: str) -> None:
    assert display_grams(Decimal(grams)) == Decimal(shown)


# --- Density storage (D60) -------------------------------------------------------------


def test_density_is_stored_to_six_decimal_places() -> None:
    assert chart("120", "1", "cup") == Decimal("0.507210")


def test_density_must_come_from_a_volume_measure() -> None:
    with pytest.raises(UnknownUnitError):
        density_from_measure(Decimal("50"), "1", "each")


# --- Reference data (seed densities from the chart) ------------------------------------


def test_every_reference_row_round_trips_to_the_charts_grams() -> None:
    rows = load_reference_densities()

    assert len(rows) >= 20
    for row in rows:
        grams = to_grams(row.quantity, row.unit, density_g_per_ml=row.density_g_per_ml)
        assert display_grams(grams) == row.grams, row.ingredient
