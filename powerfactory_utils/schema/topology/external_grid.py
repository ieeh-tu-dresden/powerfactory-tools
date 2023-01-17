# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from enum import Enum

from powerfactory_utils.schema.base import Base


class GridType(Enum):
    SL = "SL"
    PV = "PV"
    PQ = "PQ"


class ExternalGrid(Base):
    name: str
    description: str | None
    node: str
    type: GridType  # noqa: A003, VNE003
    short_circuit_power_max: float
    short_circuit_power_min: float
