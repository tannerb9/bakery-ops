"""Convert recipe quantities to grams. Pure functions: no database access.

Rules (decision log D18, D19, D59, D60):
- Everything is stored in grams. Volume needs the ingredient's density (g/ml); "each" needs
  its grams per item. If either is missing, raise. Never guess.
- Math is exact: quantities are Fractions and unit factors are exact, so 1/3 cup x 3 == 1 cup.
  Rounding happens only for display.
- US customary cup (236.5882365 ml); 16 tbsp per cup; 3 tsp per tbsp.
- Imprecise measures (rounded, heaping, pinch...) are rejected; the recipe parser asks the
  user for grams instead.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from fractions import Fraction
from pathlib import Path

QuantityInput = str | int | Decimal | Fraction


class ConversionError(ValueError):
    """Base class for every conversion failure."""


class MissingConversionError(ConversionError):
    """The ingredient lacks the density or grams-per-item this conversion needs."""


class ImpreciseMeasureError(ConversionError):
    """Measures like 'rounded tbsp' or 'pinch' have no exact weight."""


class UnknownUnitError(ConversionError):
    """The unit isn't one we support."""


class InvalidQuantityError(ConversionError):
    """The quantity isn't a non-negative number, fraction or mixed fraction."""


class Kind(Enum):
    WEIGHT = "weight"
    VOLUME = "volume"
    COUNT = "count"


# Exact factors. Weight units are in grams, volume units in millilitres.
_CUP_ML = Fraction(Decimal("236.5882365"))
_TBSP_ML = _CUP_ML / 16
_TSP_ML = _TBSP_ML / 3

_UNITS: dict[str, tuple[Kind, Fraction]] = {
    "g": (Kind.WEIGHT, Fraction(1)),
    "kg": (Kind.WEIGHT, Fraction(1000)),
    "oz": (Kind.WEIGHT, Fraction(Decimal("28.349523125"))),
    "lb": (Kind.WEIGHT, Fraction(Decimal("453.59237"))),
    "ml": (Kind.VOLUME, Fraction(1)),
    "l": (Kind.VOLUME, Fraction(1000)),
    "tsp": (Kind.VOLUME, _TSP_ML),
    "tbsp": (Kind.VOLUME, _TBSP_ML),
    "cup": (Kind.VOLUME, _CUP_ML),
    "fl oz": (Kind.VOLUME, _CUP_ML / 8),
    "each": (Kind.COUNT, Fraction(1)),
}

_ALIASES: dict[str, str] = {
    # T's shorthand (docs/shorthand.md): C, tbsp, tsp, g, ml
    "c": "cup",
    "cups": "cup",
    "gram": "g",
    "grams": "g",
    "kilogram": "kg",
    "kilograms": "kg",
    "ounce": "oz",
    "ounces": "oz",
    "pound": "lb",
    "pounds": "lb",
    "lbs": "lb",
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "fl. oz": "fl oz",
    "fluid ounce": "fl oz",
    "fluid ounces": "fl oz",
    "ea": "each",
}

_IMPRECISE = {"rnd", "rounded", "heaping", "heaped", "scant", "pinch", "dash", "smidgen"}

_QUANTITY_PATTERNS = (
    re.compile(r"^(?P<whole>\d+)$"),
    re.compile(r"^(?P<decimal>\d+\.\d*|\.\d+)$"),
    re.compile(r"^(?P<num>\d+)/(?P<den>\d+)$"),
    re.compile(r"^(?P<whole>\d+)\s+(?P<num>\d+)/(?P<den>\d+)$"),
)

_SIX_PLACES = Decimal("0.000001")


def parse_quantity(value: QuantityInput) -> Fraction:
    """Turn '2', '1.5', '1/2' or '2 1/4' into an exact Fraction. Negative values are rejected."""
    if isinstance(value, Fraction | int | Decimal):
        result = Fraction(value)
    else:
        result = _parse_quantity_text(value.strip())
    if result < 0:
        raise InvalidQuantityError(f"Quantity can't be negative: {value!r}")
    return result


def _parse_quantity_text(text: str) -> Fraction:
    for pattern in _QUANTITY_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue
        parts = match.groupdict()
        if parts.get("decimal") is not None:
            return Fraction(Decimal(parts["decimal"]))
        whole = Fraction(int(parts["whole"])) if parts.get("whole") is not None else Fraction(0)
        if parts.get("num") is None:
            return whole
        if int(parts["den"]) == 0:
            break
        return whole + Fraction(int(parts["num"]), int(parts["den"]))
    raise InvalidQuantityError(f"Not a quantity: {text!r}")


def normalize_unit(unit: str) -> str:
    """Map an alias ('C', 'Tbsp', 'grams') to its canonical unit. Rejects imprecise measures."""
    cleaned = " ".join(unit.strip().lower().split())
    if any(word in _IMPRECISE for word in cleaned.replace(".", " ").split()):
        raise ImpreciseMeasureError(
            f"'{unit}' has no exact weight. Weigh it once and enter grams instead."
        )
    canonical = _ALIASES.get(cleaned, cleaned)
    if canonical not in _UNITS:
        raise UnknownUnitError(f"Unknown unit: {unit!r}")
    return canonical


def unit_kind(unit: str) -> Kind:
    return _UNITS[normalize_unit(unit)][0]


def to_grams(
    quantity: QuantityInput,
    unit: str,
    *,
    density_g_per_ml: Decimal | None = None,
    grams_per_each: Decimal | None = None,
) -> Decimal:
    """Convert a quantity to grams at full precision. Round only for display."""
    amount = parse_quantity(quantity)
    canonical = normalize_unit(unit)
    kind, factor = _UNITS[canonical]

    if kind is Kind.WEIGHT:
        grams = amount * factor
    elif kind is Kind.VOLUME:
        if density_g_per_ml is None:
            raise MissingConversionError(
                f"Converting {canonical} to grams needs this ingredient's density."
            )
        grams = amount * factor * Fraction(density_g_per_ml)
    else:
        if grams_per_each is None:
            raise MissingConversionError("Converting a count to grams needs grams per item.")
        grams = amount * Fraction(grams_per_each)

    return Decimal(grams.numerator) / Decimal(grams.denominator)


def density_from_measure(grams: Decimal, quantity: QuantityInput, unit: str) -> Decimal:
    """Density (g/ml, 6 decimal places) from a known measure, e.g. '1 cup = 120 g'.

    Bakers know grams per cup, not g/ml; this is how a density gets entered.
    """
    canonical = normalize_unit(unit)
    kind, factor = _UNITS[canonical]
    if kind is not Kind.VOLUME:
        raise UnknownUnitError(f"Density needs a volume measure, not {unit!r}")
    millilitres = parse_quantity(quantity) * factor
    if millilitres == 0:
        raise InvalidQuantityError("Density needs a non-zero volume.")
    density = Fraction(grams) / millilitres
    exact = Decimal(density.numerator) / Decimal(density.denominator)
    return exact.quantize(_SIX_PLACES, rounding=ROUND_HALF_UP)


def display_grams(grams: Decimal) -> Decimal:
    """Round for display: 0.1 g under 10 g (precision scale), whole grams from 10 g up."""
    tenth = grams.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if tenth < 10:
        return tenth
    return grams.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ReferenceDensity:
    ingredient: str
    grams: Decimal
    quantity: str
    unit: str
    density_g_per_ml: Decimal
    source: str
    note: str


_REFERENCE_CSV = Path(__file__).parent / "data" / "reference_densities.csv"


def load_reference_densities(path: Path = _REFERENCE_CSV) -> list[ReferenceDensity]:
    """Default densities for common ingredients (suggested when a bakery adds an ingredient)."""
    rows: list[ReferenceDensity] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grams = Decimal(row["grams"])
            explicit = row["density_g_per_ml"].strip()
            density = (
                Decimal(explicit)
                if explicit
                else density_from_measure(grams, row["quantity"], row["unit"])
            )
            rows.append(
                ReferenceDensity(
                    ingredient=row["ingredient"],
                    grams=grams,
                    quantity=row["quantity"],
                    unit=row["unit"],
                    density_g_per_ml=density,
                    source=row["source"],
                    note=row["note"],
                )
            )
    return rows
