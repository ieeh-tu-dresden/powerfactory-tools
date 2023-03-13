# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import enum

import pydantic

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.base import CosphiDir


class ControlStrategy(enum.Enum):
    U_CONST = "U_CONST"
    COSPHI_CONST = "COSPHI_CONST"
    Q_CONST = "Q_CONST"
    Q_U = "Q_U"
    Q_P = "Q_P"
    COSPHI_P = "COSPHI_P"
    COSPHI_U = "COSPHI_U"
    TANPHI_CONST = "TANPHI_CONST"
    ND = "ND"


class ControlledVoltageRef(enum.Enum):
    POS_SEQ = "POS_SEQ"
    AVG = "AVG"
    A = "A"
    B = "B"
    C = "C"
    AB = "AB"
    BC = "BC"
    CA = "CA"


class ControlType(Base):
    node_target: str  # the controlled node (which can be differ from node the load is connected to)


class ControlQConst(ControlType):
    # q-setpoint control mode
    q_set: float  # Setpoint of reactive power. Counted demand based.

    control_strategy = ControlStrategy.Q_CONST


class ControlUConst(ControlType):
    # u-setpoint control mode
    u_set: float = pydantic.Field(ge=0)  # Setpoint of voltage.
    u_meas_ref: ControlledVoltageRef = ControlledVoltageRef.POS_SEQ  # voltage reference

    control_strategy = ControlStrategy.U_CONST


class ControlTanphiConst(ControlType):
    # cos(phi) control mode
    cosphi_dir: CosphiDir
    cosphi: float = pydantic.Field(ge=0, le=1)  # cos(phi) for calculation of Q in relation to P.

    control_strategy = ControlStrategy.TANPHI_CONST


class ControlCosphiConst(ControlType):
    # cos(phi) control mode
    cosphi_dir: CosphiDir
    cosphi: float = pydantic.Field(ge=0, le=1)  # cos(phi) for calculation of Q in relation to P.

    control_strategy = ControlStrategy.COSPHI_CONST


class ControlCosphiP(ControlType):
    # cos(phi(P)) control mode
    cosphi_ue: float = pydantic.Field(
        ge=0,
        le=1,
    )  # under excited: cos(phi) for calculation of Q in relation to P.
    cosphi_oe: float = pydantic.Field(
        ge=0,
        le=1,
    )  # over excited: cos(phi) for calculation of Q in relation to P.
    p_threshold_ue: float = pydantic.Field(le=0)  # under excited: threshold for P.
    p_threshold_oe: float = pydantic.Field(le=0)  # over excited: threshold for P.

    control_strategy = ControlStrategy.COSPHI_P


class ControlCosphiU(ControlType):
    # cos(phi(U)) control mode
    cosphi_ue: float = pydantic.Field(
        ...,
        ge=0,
        le=1,
    )  # under excited: cos(phi) for calculation of Q in relation to P.
    cosphi_oe: float = pydantic.Field(
        ...,
        ge=0,
        le=1,
    )  # over excited: cos(phi) for calculation of Q in relation to P.
    u_threshold_ue: float = pydantic.Field(..., ge=0)  # under excited: threshold for U.
    u_threshold_oe: float = pydantic.Field(..., ge=0)  # over excited: threshold for U.

    control_strategy = ControlStrategy.COSPHI_U


class ControlQU(ControlType):
    # Q(U) characteristic control mode
    m_tg_2015: float = pydantic.Field(
        ...,
        ge=0,
    )  # Droop/Slope based on technical guideline VDE-AR-N 4120:2015: '%/kV'-value --> Q = m_% * Pr * dU_kV
    m_tg_2018: float = pydantic.Field(
        ...,
        ge=0,
    )  # Droop/Slope based on technical guideline VDE-AR-N 4120:2018: '%/pu'-value --> Q = m_% * Pr * dU_(% of Un)
    u_q0: float = pydantic.Field(..., ge=0)  # Voltage value, where Q=0: per unit value related to Un
    u_deadband_up: float = pydantic.Field(
        ...,
        ge=0,
    )  # Width of upper deadband (U_1_up - U_Q0): per unit value related to Un
    u_deadband_low: float = pydantic.Field(
        ...,
        ge=0,
    )  # Width of lower deadband (U_Q0 - U_1_low): per unit value related to Un
    q_max_ue: float = pydantic.Field(..., ge=0)  # Under excited limit of Q: absolut value
    q_max_oe: float = pydantic.Field(..., ge=0)  # Over excited limit of Q: absolut value

    control_strategy = ControlStrategy.Q_U


def validate_pos(value: float | None) -> float | None:
    if value is not None and value < 0:
        raise ValueError

    return value


class ControlQP(ControlType):
    # Q(P) characteristic control mode
    q_p_characteristic_name: str
    q_max_ue: float | None = None  # Under excited limit of Q: absolut value
    q_max_oe: float | None = None  # Over excited limit of Q: absolut value

    control_strategy = ControlStrategy.Q_P

    validate_q_max_ue = pydantic.validator("q_max_ue", allow_reuse=True)(validate_pos)
    validate_q_max_oe = pydantic.validator("q_max_oe", allow_reuse=True)(validate_pos)


class Controller(Base):
    control_type: ControlType | None = None
    external_controller_name: str | None = None  # if external controller is specified --> name
