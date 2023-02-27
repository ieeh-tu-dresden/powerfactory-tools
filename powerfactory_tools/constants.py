# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from powerfactory_tools.api import PowerFactoryTypes as PFTypes

    UnitConversion = tuple[str, PFTypes.MetricPrefix, PFTypes.MetricPrefix]


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
    LENGTH: PFTypes.MetricPrefix = "k"
    POWER: PFTypes.MetricPrefix = "M"
    CURRENCY: PFTypes.Currency = "EUR"
    UNITCONVERSIONS: dict[str, Sequence[UnitConversion]] = {
        "ElmLodlv": [
            ("A", "", "k"),
            ("W", "k", "M"),
            ("var", "k", "M"),
            ("VA", "k", "M"),
        ],
        "ElmLodlvp": [
            ("A", "", "k"),
            ("W", "k", "M"),
            ("var", "k", "M"),
            ("VA", "k", "M"),
        ],
        "ElmPvsys": [
            ("W", "k", "M"),
            ("var", "k", "M"),
            ("VA", "k", "M"),
            ("W/Hz", "k", "M"),
        ],
    }
