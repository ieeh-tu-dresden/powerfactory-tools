from __future__ import annotations

from enum import Enum
from typing import Optional
from typing import Union

from pydantic import validator

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.base import VoltageSystemType
from powerfactory_utils.schema.topology.active_power import ActivePower
from powerfactory_utils.schema.topology.reactive_power import ReactivePower


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


PhaseConnectionType = Union[ConsumerPhaseConnectionType, ProducerPhaseConnectionType]


class ConsumerSystemType(Enum):
    FIXED = "FIXED"
    NIGHT_STORAGE = "NIGHT_STORAGE"
    VARIABLE = "VARIABLE"


class RatedPower(Base):
    s: float  # rated apparent power; base for p.u. calculation
    s_r: float  # rated apparent power (phase r)
    s_s: float  # rated apparent power (phase s)
    s_t: float  # rated apparent power (phase t)
    cosphi: Optional[float]  # rated cos(phi) in relation to rated power
    cosphi_r: Optional[float]  # rated cos(phi) (phase r)
    cosphi_s: Optional[float]  # rated cos(phi) (phase s)
    cosphi_t: Optional[float]  # rated cos(phi) (phase t)


class Load(Base):  # including assets of type load and generator
    name: str
    node: str
    description: Optional[str] = None
    u_n: float  # nominal voltage of the connected node
    rated_power: RatedPower
    active_power: ActivePower
    reactive_power: ReactivePower
    type: LoadType
    system_type: Optional[Union[ConsumerSystemType, ProducerSystemType]] = None
    phase_connection_type: Optional[PhaseConnectionType] = None
    voltage_system_type: Optional[VoltageSystemType] = None

    @validator("rated_power")
    def validate_rated_power(cls, v: RatedPower) -> RatedPower:
        cosphi = v.cosphi
        if cosphi is not None:
            if abs(cosphi) > 1 or abs(cosphi) < 0:
                raise ValueError(f"Rated `cos(phi)` must be within range [0 1], but is {cosphi}.")

        if v.s < 0:
            raise ValueError("Rated power `s` must be positive. Use type: LoadType instead.")
        return v
