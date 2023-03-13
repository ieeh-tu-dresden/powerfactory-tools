# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import enum

import pydantic  # noqa: TCH002

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.topology.windings import Winding  # noqa: TCH001


class TapSide(enum.Enum):
    HV = "HV"
    MV = "MV"
    LV = "LV"


class TransformerPhaseTechnologyType(enum.Enum):
    SINGLE_PH_E = "SINGLE_PH_E"
    SINGLE_PH = "SINGLE_PH"
    THREE_PH = "THREE_PH"


class VectorGroup(enum.Enum):
    Dd0 = "Dd0"
    Yy0 = "Yy0"
    YNy0 = "YNy0"
    Yyn0 = "Yyn0"
    YNyn0 = "YNyn0"
    Dz0 = "Dz0"
    Dzn0 = "Dzn0"
    Zd0 = "Zd0"
    ZNd0 = "ZNd0"
    Dy5 = "Dy5"
    Dyn5 = "Dyn5"
    Yd5 = "Yd5"
    YNd5 = "YNd5"
    Yz5 = "Yz5"
    YNz5 = "YNz5"
    Yzn5 = "Yzn5"
    YNzn5 = "YNzn5"
    Dd6 = "Dd6"
    Yy6 = "Yy6"
    YNy6 = "YNy6"
    Yyn6 = "Yyn6"
    YNyn6 = "YNyn6"
    Dz6 = "Dz6"
    Dzn6 = "Dzn6"
    Zd6 = "Zd6"
    ZNd6 = "ZNd6"
    Dy11 = "Dy11"
    Dyn11 = "Dyn11"
    Yd11 = "Yd11"
    YNd11 = "YNd11"
    Yz11 = "Yz11"
    YNz11 = "YNz11"
    Yzn11 = "Yzn11"
    YNzn11 = "YNzn11"


class Transformer(Base):
    node_1: str
    node_2: str
    name: str
    number: int  # number of parallel units
    vector_group: VectorGroup  # specifier for connection of wiring e.g. DYn5
    i_0: float  # no-load current in %
    p_fe: float  # no-load losses (Iron losses)
    windings: pydantic.conlist(Winding, unique_items=True)  # type: ignore[valid-type]  # winding object for each voltage level
    phase_technology_type: TransformerPhaseTechnologyType | None = None  # three- or single-phase-transformer
    description: str | None = None
    tap_u_abs: float | None = None  # voltage deviation per tap position change in %
    tap_u_phi: float | None = None  # voltage angle deviation per tap position in °
    tap_max: int | None = None  # upper position of tap for tap control
    tap_min: int | None = None  # lower position of tap for tap control
    tap_neutral: int | None = None  # initial position where rated transformation ratio is specified
    tap_side: TapSide | None = None  # transformer side of where tap changer is installed
