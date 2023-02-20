# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from enum import Enum

from powerfactory_tools.schema.base import Base


class GridType(Enum):
    SL = "SL"  # slack node: voltage amplitude and phase angle is fixed
    PV = "PV"  # active power and voltage amplitude is fixed
    PQ = "PQ"  # active power and reactive power is fixed


class ExternalGrid(Base):
    name: str
    description: str | None
    node: str
    type: GridType  # noqa: A003
    short_circuit_power_max: float
    short_circuit_power_min: float
