# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from enum import Enum

import pydantic

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.base import VoltageSystemType
from powerfactory_tools.schema.topology.active_power import ActivePower  # noqa: TCH001
from powerfactory_tools.schema.topology.reactive_power import ReactivePower  # noqa: TCH001


class CosphiDir(Enum):
    UE = "UE"  # under excited operation
    OE = "OE"  # over excited operation


class LoadType(Enum):
    CONSUMER = "CONSUMER"
    PRODUCER = "PRODUCER"


class ProducerSystemType(Enum):
    COAL = "COAL"  # coal
    OIL = "OIL"  # oil
    GAS = "GAS"  # gas
    DIESEL = "DIESEL"  # dies
    NUCLEAR = "NUCLEAR"  # nuc
    HYDRO = "HYDRO"  # hydr
    PUMP_STORAGE = "PUMP_STORAGE"  # pump
    WIND = "WIND"  # wgen
    BIOGAS = "BIOGAS"  # bgas
    SOLAR = "SOLAR"  # sol
    PV = "PV"  # pv
    RENEWABLE_ENERGY = "RENEWABLE_ENERGY"  # reng
    FUELCELL = "FUELCELL"  # fc
    PEAT = "PEAT"  # peat
    STAT_GEN = "STAT_GEN"  # stg
    HVDC = "HVDC"  # hvdc
    REACTIVE_POWER_COMPENSATOR = "REACTIVE_POWER_COMPENSATOR"  # rpc
    BATTERY_STORAGE = "BATTERY_STORAGE"  # stor
    EXTERNAL_GRID_EQUIVALENT = "EXTERNAL_GRID_EQUIVALENT"  # net
    OTHERS = "OTHERS"  # othg


class ConsumerPhaseConnectionType(Enum):
    THREE_PH_D = "3PH_D"  # 0
    THREE_PH_PH_E = "3PH_PH-E"  # 2
    THREE_PH_YN = "3PH_YN"  # 3
    TWO_PH_PH_E = "2PH_PH-E"  # 4
    TWO_PH_YN = "2PH_YN"  # 5
    ONE_PH_PH_PH = "1PH_PH-PH"  # 7
    ONE_PH_PH_E = "1PH_PH-E"  # 8
    ONE_PH_PH_N = "1PH_PH-N"  # 9


class ProducerPhaseConnectionType(Enum):
    THREE_PH = "3PH"  # 0
    THREE_PH_E = "3PH-E"  # 1
    ONE_PH_PH_E = "1PH_PH-E"  # 2
    ONE_PH_PH_N = "1PH_PH-N"  # 3
    ONE_PH_PH_PH = "1PH_PH-PH"  # 4


PhaseConnectionType = ConsumerPhaseConnectionType | ProducerPhaseConnectionType


class ConsumerSystemType(Enum):
    FIXED = "FIXED"
    NIGHT_STORAGE = "NIGHT_STORAGE"
    VARIABLE = "VARIABLE"


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
    description: str | None = None
    u_n: float  # nominal voltage of the connected node
    rated_power: RatedPower
    active_power: ActivePower
    reactive_power: ReactivePower
    type: LoadType  # noqa: A003
    system_type: ConsumerSystemType | ProducerSystemType | None = None
    phase_connection_type: PhaseConnectionType | None = None
    voltage_system_type: VoltageSystemType | None = None
