# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2025.
# :license: BSD 3-Clause

from __future__ import annotations

import typing as t

from powerfactory_tools.versions.pf2024.types import Currency
from powerfactory_tools.versions.pf2024.types import MetricPrefix

if t.TYPE_CHECKING:
    from collections.abc import Sequence

    UnitConversion = tuple[str, MetricPrefix, MetricPrefix]

DEFAULT_PHASE_QUANTITY = 3


class Exponents:
    CONDUCTANCE: float = 10**-6
    CURRENT: float = 10**3
    LENGTH: float = 10**3
    POWER: float = 10**6
    REACTANCE: float = 10**0
    RESISTANCE: float = 10**0
    SUSCEPTANCE: float = 10**-6
    VOLTAGE: float = 10**3


class DecimalDigits:
    ADMITTANCE: int = 13
    ANGLE: int = 5
    CURRENT: int = 2
    FREQUENCY: int = 4
    IMPEDANCE: int = 7
    POWER: int = 1
    POWERFACTOR: int = 7
    PU: int = 5
    VOLTAGE: int = 2


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
