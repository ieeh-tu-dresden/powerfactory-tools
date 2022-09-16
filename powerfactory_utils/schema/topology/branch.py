from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from powerfactory_utils.schema.base import VoltageSystemType


class BranchType(Enum):
    LINE = "LINE"
    COUPLER = "COUPLER"


class Branch(BaseModel):
    node_1: str
    node_2: str
    name: str
    u_n: float  # nominal voltage of the branch connected nodes
    i_r: float  # rated current of branch (thermal limit in continuous operation)
    r1: float  # positive sequence values of PI-representation
    x1: float  # positive sequence values of PI-representation
    g1: float  # positive sequence values of PI-representation
    b1: float  # positive sequence values of PI-representation
    type: BranchType
    voltage_system_type: Optional[VoltageSystemType] = None
    r0: Optional[float] = None  # zero sequence values of PI-representation
    x0: Optional[float] = None  # zero sequence values of PI-representation
    g0: Optional[float] = None  # zero sequence values of PI-representation
    b0: Optional[float] = None  # zero sequence values of PI-representation
    f_n: Optional[float] = None  # nominal frequency the values x and b apply
    description: Optional[str] = None
    energized: Optional[bool] = None
