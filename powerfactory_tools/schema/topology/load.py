# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import enum
from collections.abc import Sequence

import pydantic

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.base import VoltageSystemType
from powerfactory_tools.schema.topology.active_power import ActivePower  # noqa: TCH001
from powerfactory_tools.schema.topology.reactive_power import ReactivePower  # noqa: TCH001


class CosphiDir(enum.Enum):
    UE = enum.auto()
    OE = enum.auto()


class LoadType(enum.Enum):
    CONSUMER = enum.auto()
    PRODUCER = enum.auto()


class ProducerSystemType(enum.Enum):
    COAL = enum.auto()
    OIL = enum.auto()
    GAS = enum.auto()
    DIESEL = enum.auto()
    NUCLEAR = enum.auto()
    HYDRO = enum.auto()
    PUMP_STORAGE = enum.auto()
    WIND = enum.auto()
    BIOGAS = enum.auto()
    SOLAR = enum.auto()
    PV = enum.auto()
    RENEWABLE_ENERGY = enum.auto()
    FUELCELL = enum.auto()
    PEAT = enum.auto()
    STAT_GEN = enum.auto()
    HVDC = enum.auto()
    REACTIVE_POWER_COMPENSATOR = enum.auto()
    BATTERY_STORAGE = enum.auto()
    EXTERNAL_GRID_EQUIVALENT = enum.auto()
    OTHER = enum.auto()


class PhaseConnectionType(enum.Enum):
    THREE_PH_D = enum.auto()
    THREE_PH_PH_E = enum.auto()
    THREE_PH_YN = enum.auto()
    TWO_PH_PH_E = enum.auto()
    TWO_PH_YN = enum.auto()
    ONE_PH_PH_PH = enum.auto()
    ONE_PH_PH_E = enum.auto()
    ONE_PH_PH_N = enum.auto()


class Phase(enum.Enum):
    A = enum.auto()
    B = enum.auto()
    C = enum.auto()


class ConsumerSystemType(enum.Enum):
    FIXED = "CONSUMER_FIXED"
    NIGHT_STORAGE = "NIGHT_STORAGE"
    VARIABLE = "CONSUMER_VARIABLE"


THRESHOLD = 0.51  # acceptable rounding error (0.5 W) + epsilon for calculation accuracy (0.01 W)


def validate_total(values: dict[str, float]) -> dict[str, float]:
    pow_total = values["value_a"] + values["value_b"] + values["value_c"]
    diff = abs(values["value"] - pow_total)
    if diff > THRESHOLD:
        msg = f"Power mismatch: Total power should be {pow_total}, is {values['value']}."
        raise ValueError(msg)

    return values


def validate_symmetry(values: dict[str, float]) -> dict[str, float]:
    if values["is_symmetrical"] and not (values["value_a"] == values["value_b"] == values["value_c"]):
        msg = "Power mismatch: Three-phase power of load is not symmetrical."
        raise ValueError(msg)

    return values


class RatedPower(Base):
    value: float = pydantic.Field(..., ge=0)  # rated apparent power; base for p.u. calculation
    value_a: float = pydantic.Field(..., ge=0)  # rated apparent power (phase a)
    value_b: float = pydantic.Field(..., ge=0)  # rated apparent power (phase b)
    value_c: float = pydantic.Field(..., ge=0)  # rated apparent power (phase c)
    cosphi: float = pydantic.Field(1, ge=0, le=1)  # rated cos(phi) in relation to rated power
    cosphi_a: float = pydantic.Field(1, ge=0, le=1)  # rated cos(phi) (phase a)
    cosphi_b: float = pydantic.Field(1, ge=0, le=1)  # rated cos(phi) (phase b)
    cosphi_c: float = pydantic.Field(1, ge=0, le=1)  # rated cos(phi) (phase c)

    @pydantic.root_validator(skip_on_failure=True)
    def _validate_total(cls, values: dict[str, float]) -> dict[str, float]:
        return validate_total(values)


class Load(Base):  # including assets of type load and generator
    name: str
    node: str
    u_n: float  # nominal voltage of the connected node
    rated_power: RatedPower
    active_power: ActivePower
    reactive_power: ReactivePower
    type: LoadType  # noqa: A003
    connected_phases: Sequence[Phase]
    system_type: ConsumerSystemType | ProducerSystemType
    phase_connection_type: PhaseConnectionType
    voltage_system_type: VoltageSystemType
    description: str | None = None
