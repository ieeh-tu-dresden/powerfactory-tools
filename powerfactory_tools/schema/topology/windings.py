# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import enum

from powerfactory_tools.schema.base import Base


class VectorGroup(enum.Enum):
    Y = "Y"
    YN = "YN"
    Z = "Z"
    ZN = "ZN"
    D = "D"


class Winding(Base):
    node: str
    s_r: float
    u_n: float  # Nominal Voltage of connected nodes (CIM: BaseVoltage)
    u_r: float  # Rated Voltage of the transformer windings itself (CIM: ratedU)
    r1: float  # positive sequence values of transformer T-representation
    x1: float
    r0: float | None = None  # zero sequence values of transformer T-representation
    x0: float | None = None
    phase_angle_clock: int | None = None
    vector_group: VectorGroup | None = None
