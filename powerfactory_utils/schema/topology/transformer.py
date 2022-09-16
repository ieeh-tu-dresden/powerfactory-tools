from __future__ import annotations

from enum import Enum
from typing import Optional
from typing import Sequence

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.topology.windings import Winding


class TapSide(Enum):
    HV = "HV"  # high voltage side of transformer
    MV = "MV"  # medium voltage side of transformer (only if 3 winding)
    LV = "LV"  # low voltage side of transformer


class TransformerPhaseTechnologyType(Enum):
    SINGLE_PH_E = "1PH-E"  # Single Phase Transformer, earthed
    SINGLE_PH = "1PH"  # Single Phase Transformer
    THREE_PH = "3PH"  # Three Phase Transformer


class Transformer(Base):
    node_1: str
    node_2: str
    name: str
    number: int  # number of parallel units
    vector_group: str  # specifier for connection of wiring e.g. DYn5
    i_0: float  # no-load current in %
    p_fe: float  # no-load losses (Iron losses)
    windings: Sequence[Winding]  # winding object for each voltage level
    phase_technology_type: Optional[TransformerPhaseTechnologyType] = None  # three- or single-phase-transformer
    description: Optional[str] = None
    tap_u_abs: Optional[float] = None  # voltage deviation per tap position change in %
    tap_u_phi: Optional[float] = None  # voltage angle deviation per tap position in °
    tap_max: Optional[int] = None  # upper position of tap for tap control
    tap_min: Optional[int] = None  # lower position of tap for tap control
    tap_neutral: Optional[int] = None  # initial position where rated transformation ratio is specified
    tap_side: Optional[TapSide] = None  # transformer side of where tap changer is installed
