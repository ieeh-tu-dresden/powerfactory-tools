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


def validate_cosphi(cosphi: float) -> float:
    if cosphi is not None and (abs(cosphi) > 1 or abs(cosphi) < 0):
        msg = f"Rated {cosphi=} must be within range [0 1]."
        raise ValueError(msg)

    return cosphi


def validate_power(power: float) -> float:
    if power < 0:
        msg = f"Rated {power=} must be positive."
        raise ValueError(msg)

    return power


class RatedPower(Base):
    value: float  # rated apparent power; base for p.u. calculation
    value_a: float  # rated apparent power (phase a)
    value_b: float  # rated apparent power (phase b)
    value_c: float  # rated apparent power (phase c)
    cosphi_ue: float = 1  # rated cos(phi) in relation to rated power
    cosphi_a_ue: float = 1  # rated cos(phi) (phase a)
    cosphi_b_ue: float = 1  # rated cos(phi) (phase b)
    cosphi_c_ue: float = 1  # rated cos(phi) (phase c)
    cosphi_oe: float = 1  # rated cos(phi) in relation to rated power
    cosphi_a_oe: float = 1  # rated cos(phi) (phase a)
    cosphi_b_oe: float = 1  # rated cos(phi) (phase b)
    cosphi_c_oe: float = 1  # rated cos(phi) (phase c)

    _validate_cosphi_ue = pydantic.validator("cosphi_ue", allow_reuse=True)(validate_cosphi)
    _validate_cosphi_a_ue = pydantic.validator("cosphi_a_ue", allow_reuse=True)(validate_cosphi)
    _validate_cosphi_b_ue = pydantic.validator("cosphi_b_ue", allow_reuse=True)(validate_cosphi)
    _validate_cosphi_c_ue = pydantic.validator("cosphi_c_ue", allow_reuse=True)(validate_cosphi)
    _validate_cosphi_oe = pydantic.validator("cosphi_oe", allow_reuse=True)(validate_cosphi)
    _validate_cosphi_a_oe = pydantic.validator("cosphi_a_oe", allow_reuse=True)(validate_cosphi)
    _validate_cosphi_b_oe = pydantic.validator("cosphi_b_oe", allow_reuse=True)(validate_cosphi)
    _validate_cosphi_c_oe = pydantic.validator("cosphi_c_oe", allow_reuse=True)(validate_cosphi)
    _validate_power = pydantic.validator("value", allow_reuse=True)(validate_power)
    _validate_power_a = pydantic.validator("value_a", allow_reuse=True)(validate_power)
    _validate_power_b = pydantic.validator("value_b", allow_reuse=True)(validate_power)
    _validate_power_c = pydantic.validator("value_c", allow_reuse=True)(validate_power)


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
