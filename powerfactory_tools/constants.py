# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import decimal
import typing as t

from powerfactory_tools.powerfactory_types import Currency
from powerfactory_tools.powerfactory_types import MetricPrefix

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    UnitConversion = tuple[str, MetricPrefix, MetricPrefix]


def convert_exponent_in_decimal_digit(exp: float) -> int:
    dec = decimal.Decimal(str(exp))
    digit = dec.as_tuple().exponent
    if type(digit) == int:
        return -1 * digit
    return 0


class Exponents:
    VOLTAGE: float = 10**3
    CURRENT: float = 10**3
    RESISTANCE: float = 10**0
    REACTANCE: float = 10**0
    SUSCEPTANCE: float = 10**-6
    CONDUCTANCE: float = 10**-6
    POWER: float = 10**6


class DecimalDigits:
    COSPHI: int = 6
    VOLTAGE: int = 1
    CURRENT: int = 1
    POWER: int = 0
    PU: int = 4
    IMPEDANCE: int = 6


class BaseUnits:
    LENGTH: MetricPrefix = MetricPrefix.k
    POWER: MetricPrefix = MetricPrefix.M
    CURRENCY: Currency = Currency.EUR
    UNITCONVERSIONS: t.ClassVar[dict[str, Sequence[UnitConversion]]] = {
        "ElmLodlv": [
            ("A", MetricPrefix.EMPTY, MetricPrefix.k),
            ("W", MetricPrefix.k, MetricPrefix.M),
            ("var", MetricPrefix.k, MetricPrefix.M),
            ("VA", MetricPrefix.k, MetricPrefix.M),
        ],
        "ElmLodlvp": [
            ("A", MetricPrefix.EMPTY, MetricPrefix.k),
            ("W", MetricPrefix.k, MetricPrefix.M),
            ("var", MetricPrefix.k, MetricPrefix.M),
            ("VA", MetricPrefix.k, MetricPrefix.M),
        ],
        "ElmPvsys": [
            ("W", MetricPrefix.k, MetricPrefix.M),
            ("var", MetricPrefix.k, MetricPrefix.M),
            ("VA", MetricPrefix.k, MetricPrefix.M),
            ("W/Hz", MetricPrefix.k, MetricPrefix.M),
        ],
    }
