# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

from powerfactory_tools.powerfactory_types import Currency
from powerfactory_tools.powerfactory_types import MetricPrefix

if TYPE_CHECKING:
    from collections.abc import Sequence

    UnitConversion = tuple[str, MetricPrefix, MetricPrefix]


class Exponents:
    VOLTAGE = 10**3
    CURRENT = 10**3
    RESISTANCE = 1
    REACTANCE = 1
    SUSCEPTANCE = 10**-6
    CONDUCTANCE = 10**-6
    POWER = 10**6


class DecimalDigits:
    COSPHI = 6
    VOLTAGE = 1
    CURRENT = 1
    POWER = 0
    PU = 4


class BaseUnits:
    LENGTH: MetricPrefix = MetricPrefix.k
    POWER: MetricPrefix = MetricPrefix.M
    CURRENCY: Currency = Currency.EUR
    UNITCONVERSIONS: dict[str, Sequence[UnitConversion]] = {
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
