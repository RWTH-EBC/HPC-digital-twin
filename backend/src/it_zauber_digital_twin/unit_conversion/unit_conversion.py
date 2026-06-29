from typing import Dict
import polars as pl


def get_unit_conversion_expressions(
    points: Dict[str, str],
):
    """
    Generate conversion expressions for converting to and from SI units.

    Args:
        points: Dictionary mapping point names to their units

    """

    TO_SI_CONVERSIONS = {
        "degree_celsius": lambda col: col + 273.15,
        "watt": lambda col: col,
        "rpm": lambda col: col,
        "kilowatt": lambda col: col * 1000,
        "m^3/h": lambda col: col / 3.6,
        "bar": lambda col: col * 1e5,
        "mbar": lambda col: col * 100,
        "percent": lambda col: col / 100,
    }

    FROM_SI_CONVERSIONS = {
        "degree_celsius": lambda col: col - 273.15,
        "watt": lambda col: col,
        "rpm": lambda col: col,
        "kilowatt": lambda col: col / 1000,
        "m^3/h": lambda col: col * 3.6,
        "bar": lambda col: col / 1e5,
        "mbar": lambda col: col / 100,
        "percent": lambda col: col * 100,
    }

    to_si_expressions = {}
    from_si_expressions = {}

    for unit, points_list in points.items():
        if unit == "unitless":
            continue
        elif "_keep" in unit:
            continue 
        if unit in TO_SI_CONVERSIONS:
            for point in points_list:
                to_si_expr = TO_SI_CONVERSIONS[unit](pl.col(point)).alias(point)
                from_si_expr = FROM_SI_CONVERSIONS[unit](pl.col(point)).alias(point)
                to_si_expressions[point] = to_si_expr
                from_si_expressions[point] = from_si_expr
        else:
            raise ValueError(f"Unsupported unit for conversion: {unit}")

    return to_si_expressions, from_si_expressions
