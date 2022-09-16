from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from typing import Optional

from pydantic import root_validator
from pydantic.class_validators import validator

from powerfactory_utils.schema.base import Base

if TYPE_CHECKING:
    from typing import Any


class CosphiDir(Enum):
    UE = "UE"  # under excited operation
    OE = "OE"  # over excited operation


class ControllerType(Enum):
    U_CONST = "U_CONST"
    COSPHI_CONST = "COSPHI_CONST"
    Q_CONST = "Q_CONST"
    Q_U = "Q_U"
    Q_P = "Q_P"
    COSPHI_P = "COSPHI_P"
    COSPHI_U = "COSPHI_U"
    TANPHI_CONST = "TANPHI_CONST"
    ND = "ND"


class Controller(Base):
    controller_type: ControllerType
    external_controller_name: Optional[str] = None  # if external controller is specified --> name
    # cos(phi) control mode
    cosphi_type: Optional[CosphiDir] = None  # CosphiDir
    cosphi: Optional[float] = None  # cos(phi) for calculation of Q in relation to P.
    # q-setpoint control mode
    q_set: Optional[float] = None  # Setpoint of reactive power.
    # Q(U) characteristic control mode
    m_tab2015: Optional[float] = None  # Droop based on VDE-AR-N 4120:2015: '%'-value --> Q = m_% * Pr * dU_kV
    m_tar2018: Optional[float] = None  # Droop based on VDE-AR-N 4120:2018: '%'-value --> Q = m_% * Pr * dU_(% of Un)
    u_q0: Optional[float] = None  # Voltage value, where Q=0: per unit value related to Un
    udeadband_up: Optional[float] = None  # Width of upper deadband (U_1_up - U_Q0): per unit value related to Un
    udeadband_low: Optional[float] = None  # Width of lower deadband (U_Q0 - U_1_low): per unit value related to Un
    qmax_ue: Optional[float] = None  # Over excited limit of Q: absolut per unit value related to Pr
    qmax_oe: Optional[float] = None  # Under excited limit of Q: absolut per unit value related to Pr

    class Config:
        frozen = True

    @validator("cosphi")
    def validate_cosphi(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if not (-1 <= v <= 1):
                raise ValueError(f"Cosphi must be between -1 and 1, but is {v}.")
        return v

    @validator("qmax_ue")
    def validate_qmax_ue(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if not (0 <= v):
                raise ValueError(
                    f"qmax_ue must be greater/equal than 0(p.u.), as it is defined as absolut value, but is {v}."
                )
        return v

    @validator("qmax_oe")
    def validate_qmax_oe(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if not (0 <= v):
                raise ValueError(
                    f"qmax_oe must be greater/equal than 0(p.u.), as it is defined as absolut value, but is {v}."
                )
        return v

    @validator("udeadband_up")
    def validate_udeadband_up(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if not (0 <= v):
                raise ValueError(
                    f"udeadband_up must be greater/equal than 0(p.u.), as it is defined as absolut value, but is {v}."
                )
        return v

    @validator("udeadband_low")
    def validate_udeadband_low(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if not (0 <= v):
                raise ValueError(
                    f"udeadband_low must be greater/equal than 0(p.u.), as it is defined as absolut value, but is {v}."
                )
        return v

    @root_validator()
    def validate_controller_type(cls, values: dict[str, Any]) -> dict[str, Any]:
        t = values["controller_type"]
        if t == t.COSPHI_CONST:
            if values["cosphi"] is None:
                raise ValueError("cosphi must be specified for constant-Cosphi-control.")
            if values["cosphi_type"] is None:
                raise ValueError("cosphi_type must be specified for constant-Cosphi-control.")
        elif t == t.Q_CONST:
            if values["q_set"] is None:
                raise ValueError("q_set must be specified for Q-setpoint-control.")
        elif t == t.Q_U:
            if values["u_q0"] is None:
                raise ValueError("u_q0 must be specified for Q(U)-characteristic-control.")
            if values["udeadband_up"] is None:
                raise ValueError("udeadband_up must be specified for Q(U)-characteristic-control.")
            if values["udeadband_low"] is None:
                raise ValueError("udeadband_low must be specified for Q(U)-characteristic-control.")
            if values["qmax_oe"] is None:
                raise ValueError("qmax_oe must be specified for Q(U)-characteristic-control.")
            if values["qmax_ue"] is None:
                raise ValueError("qmax_ue must be specified for Q(U)-characteristic-control.")
            if values["m_tab2015"] is None and values["m_tar2018"] is None:
                raise ValueError("Either m_tab2015 or m_tar2018 must be specified for Q(U)-characteristic-control.")
        elif t == t.TANPHI_CONST:
            if values["cosphi"] is None:
                raise ValueError("cosphi must be specified for constant-Tanphi-control.")
            if values["cosphi_type"] is None:
                raise ValueError("cosphi_type must be specified for constant-Tanphi-control.")
        return values
