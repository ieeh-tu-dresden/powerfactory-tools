from powerfactory_utils import powerfactory_types as pft

UnitConversion = tuple[str, pft.MetricPrefix, pft.MetricPrefix]


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
    VOLTAGE = 3
    CURRENT = 3
    POWER = 0
    PU = 4


class BaseUnits:
    LENGTH: pft.MetricPrefix = "k"
    POWER: pft.MetricPrefix = "M"
    CURRENCY: pft.Currency = "EUR"
    UNITCONVERSIONS: dict[str, list[UnitConversion]] = {
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
