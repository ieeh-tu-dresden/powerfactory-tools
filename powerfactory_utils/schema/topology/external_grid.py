from __future__ import annotations

from enum import Enum
from typing import Optional

from powerfactory_utils.schema.base import Base


class GridType(Enum):
    SL = "SL"
    PV = "PV"
    PQ = "PQ"


class ExternalGrid(Base):
    name: str
    description: Optional[str]
    node: str
    type: GridType
    short_circuit_power_max: float
    short_circuit_power_min: float
