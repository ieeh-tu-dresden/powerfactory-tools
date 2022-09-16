from __future__ import annotations

from typing import Optional

from powerfactory_utils.schema.base import Base


class Winding(Base):
    node: str
    s_r: float
    u_n: float  # Nominal Voltage of connected nodes (CIM: BaseVoltage)
    u_r: float  # Rated Voltage of the transformer windings itself (CIM: ratedU)
    r1: float  # positive sequence values of transformer T-representation
    x1: float
    r0: Optional[float] = None  # zero sequence values of transformer T-representation
    x0: Optional[float] = None
    phase_angle_clock: Optional[int] = None
    vector_group: Optional[str] = None
