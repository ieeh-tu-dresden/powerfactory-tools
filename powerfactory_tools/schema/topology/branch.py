# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from enum import Enum

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.base import VoltageSystemType


class BranchType(Enum):
    LINE = "LINE"
    COUPLER = "COUPLER"


class Branch(Base):
    node_1: str
    node_2: str
    name: str
    u_n: float  # nominal voltage of the branch connected nodes
    i_r: float  # rated current of branch (thermal limit in continuous operation)
    r1: float  # positive sequence values of PI-representation
    x1: float  # positive sequence values of PI-representation
    g1: float  # positive sequence values of PI-representation
    b1: float  # positive sequence values of PI-representation
    type: BranchType  # noqa: A003
    voltage_system_type: VoltageSystemType
    r0: float | None = None  # zero sequence values of PI-representation
    x0: float | None = None  # zero sequence values of PI-representation
    g0: float | None = None  # zero sequence values of PI-representation
    b0: float | None = None  # zero sequence values of PI-representation
    f_n: float | None = None  # nominal frequency the values x and b apply
    description: str | None = None
    energized: bool | None = None
