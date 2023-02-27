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
    HV = enum.auto()
    MV = enum.auto()
    LV = enum.auto()


class TransformerPhaseTechnologyType(enum.Enum):
    SINGLE_PH_E = enum.auto()
    SINGLE_PH = enum.auto()
    THREE_PH = enum.auto()


class VectorGroup(enum.Enum):
    Dd0 = enum.auto()
    Yy0 = enum.auto()
    YNy0 = enum.auto()
    Yyn0 = enum.auto()
    YNyn0 = enum.auto()
    Dz0 = enum.auto()
    Dzn0 = enum.auto()
    Zd0 = enum.auto()
    ZNd0 = enum.auto()
    Dy5 = enum.auto()
    Dyn5 = enum.auto()
    Yd5 = enum.auto()
    YNd5 = enum.auto()
    Yz5 = enum.auto()
    YNz5 = enum.auto()
    Yzn5 = enum.auto()
    YNzn5 = enum.auto()
    Dd6 = enum.auto()
    Yy6 = enum.auto()
    YNy6 = enum.auto()
    Yyn6 = enum.auto()
    YNyn6 = enum.auto()
    Dz6 = enum.auto()
    Dzn6 = enum.auto()
    Zd6 = enum.auto()
    ZNd6 = enum.auto()
    Dy11 = enum.auto()
    Dyn11 = enum.auto()
    Yd11 = enum.auto()
    YNd11 = enum.auto()
    Yz11 = enum.auto()
    YNz11 = enum.auto()
    Yzn11 = enum.auto()
    YNzn11 = enum.auto()


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
