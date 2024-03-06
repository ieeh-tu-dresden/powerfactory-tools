# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import enum


class MetricPrefix(enum.Enum):
    a = "a"
    f = "f"
    p = "p"
    n = "n"
    u = "u"
    m = "m"
    EMPTY = ""
    k = "k"
    M = "M"
    G = "G"
    T = "T"
    P = "P"
    E = "E"


class Currency(enum.Enum):
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    GBP = "GBP"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"
    CNY = "CNY"
    SEK = "SEK"
    MXN = "MXN"
    NZD = "NZD"
    SGD = "SGD"
    HKD = "HKD"
    NOK = "NOK"
    KRW = "KRW"
    TRY = "TRY"
    INR = "INR"
    RUB = "RUB"
    BRL = "BRL"
    ZAR = "ZAR"
    CLP = "CLP"
