# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import pydantic

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.topology.load import CosphiDir  # noqa: TCH001

if TYPE_CHECKING:
    from typing import Any


class ControlStrategy(Enum):
    U_CONST = "U_CONST"
    COSPHI_CONST = "COSPHI_CONST"
    Q_CONST = "Q_CONST"
    Q_U = "Q_U"
    Q_P = "Q_P"
    COSPHI_P = "COSPHI_P"
    COSPHI_U = "COSPHI_U"
    TANPHI_CONST = "TANPHI_CONST"
    ND = "ND"


class ControlledVoltageRef(Enum):
    POS_SEQUENCE = "POSITIVE SEQUENCE"
    AVERAGE = "AVERAGE"
    A = "A"
    B = "B"
    C = "C"
    AB = "AB"
    BC = "BC"
    CA = "CA"


class ControlBase(Base):
    node_target: str | None = None  # the controlled node (which can be differ from node the load is connected to)


class ControlQConst(ControlBase):
    # q-setpoint control mode
    control_strategy = ControlStrategy.Q_CONST
    q_set: float  # Setpoint of reactive power. Counted demand based.

    @pydantic.root_validator()
    def validate_q_const_controller(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["q_set"] is None:
            raise Exceptions.QSetNotSpecifiedError

        return values


class ControlUConst(ControlBase):
    # u-setpoint control mode
    control_strategy = ControlStrategy.U_CONST
    u_set: float  # Setpoint of voltage.
    u_meas_tref: ControlledVoltageRef = ControlledVoltageRef.POS_SEQUENCE  # voltage reference

    @pydantic.root_validator()
    def validate_u_const_controller(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["u_set"] is None:
            raise Exceptions.USetNotSpecifiedError

        if values["u_meas_tref"] is None:
            raise Exceptions.UMeasRefNotSpecifiedError

        return values


class ControlTanphiConst(ControlBase):
    # cos(phi) control mode
    control_strategy = ControlStrategy.TANPHI_CONST
    cosphi_dir: CosphiDir  # CosphiDir
    cosphi: float = pydantic.Field(ge=0, le=1)  # cos(phi) for calculation of Q in relation to P.

    @pydantic.root_validator()
    def validate_tanphi_const_controller(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["cosphi"] is None:
            msg = "cosphi must be specified for constant-tanphi-control."
            raise ValueError(msg)

        if values["cosphi_dir"] is None:
            msg = "cosphi_dir must be specified for constant-tanphi-control."
            raise ValueError(msg)

        return values


class ControlCosphiConst(ControlBase):
    # cos(phi) control mode
    control_strategy = ControlStrategy.COSPHI_CONST
    cosphi_dir: CosphiDir  # CosphiDir
    cosphi: float = pydantic.Field(ge=0, le=1)  # cos(phi) for calculation of Q in relation to P.

    @pydantic.root_validator()
    def validate_cosphi_const_controller(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["cosphi"] is None:
            msg = "cosphi must be specified for constant-cosphi-control."
            raise ValueError(msg)

        if values["cosphi_dir"] is None:
            msg = "cosphi_dir must be specified for constant-cosphi-control."
            raise ValueError(msg)

        return values


class ControlCosphiP(ControlBase):
    # cos(phi(P)) control mode
    control_strategy = ControlStrategy.COSPHI_P
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

    @pydantic.root_validator()
    def validate_cosphi_p_controller(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["cosphi_ue"] is None:
            msg = "cosphi_ue must be specified for cosphi(P)-control."
            raise ValueError(msg)

        if values["cosphi_oe"] is None:
            msg = "cosphi_oe must be specified for cosphi(P)-control."
            raise ValueError(msg)

        if values["p_threshold_ue"] is None:
            raise Exceptions.PThresholdUeNotSpecifiedError

        if values["p_threshold_oe"] is None:
            raise Exceptions.PThresholdOeNotSpecifiedError

        return values


class ControlCosphiU(ControlBase):
    # cos(phi(U)) control mode
    control_strategy = ControlStrategy.COSPHI_U
    cosphi_ue: float = pydantic.Field(
        ge=0,
        le=1,
    )  # under excited: cos(phi) for calculation of Q in relation to P.
    cosphi_oe: float = pydantic.Field(
        ge=0,
        le=1,
    )  # over excited: cos(phi) for calculation of Q in relation to P.
    u_threshold_ue: float = pydantic.Field(ge=0)  # under excited: threshold for U.
    u_threshold_oe: float = pydantic.Field(ge=0)  # over excited: threshold for U.

    @pydantic.root_validator()
    def validate_cosphi_u_controller(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["cosphi_ue"] is None:
            msg = "cosphi_ue must be specified for cosphi(U)-control."
            raise ValueError(msg)

        if values["cosphi_oe"] is None:
            msg = "cosphi_oe must be specified for cosphi(U)-control."
            raise ValueError(msg)

        if values["u_threshold_ue"] is None:
            raise Exceptions.UThresholdUeNotSpecifiedError

        if values["u_threshold_oe"] is None:
            raise Exceptions.UThresholdOeNotSpecifiedError

        return values


class ControlQU(ControlBase):
    # Q(U) characteristic control mode
    control_strategy = ControlStrategy.Q_U
    m_tg_2015: float = pydantic.Field(
        ge=0,
    )  # Droop/Slope based on technical guideline VDE-AR-N 4120:2015: '%/kV'-value --> Q = m_% * Pr * dU_kV
    m_tg_2018: float = pydantic.Field(
        ge=0,
    )  # Droop/Slope based on technical guideline VDE-AR-N 4120:2018: '%/pu'-value --> Q = m_% * Pr * dU_(% of Un)
    u_q0: float = pydantic.Field(ge=0)  # Voltage value, where Q=0: per unit value related to Un
    u_deadband_up: float = pydantic.Field(
        ge=0,
    )  # Width of upper deadband (U_1_up - U_Q0): per unit value related to Un
    u_deadband_low: float = pydantic.Field(
        ge=0,
    )  # Width of lower deadband (U_Q0 - U_1_low): per unit value related to Un
    q_max_ue: float = pydantic.Field(ge=0)  # Under excited limit of Q: absolut value
    q_max_oe: float = pydantic.Field(ge=0)  # Over excited limit of Q: absolut value

    @pydantic.root_validator()
    def validate_q_u_controller(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["u_q0"] is None:
            raise Exceptions.UQ0NotSpecifiedError

        if values["u_deadband_up"] is None:
            raise Exceptions.UdeadbandUpNotSpecifiedError

        if values["u_deadband_low"] is None:
            raise Exceptions.UdeadbandLowNotSpecifiedError

        if values["q_max_oe"] is None:
            msg = "q_max_oe must be specified for Q(U)-characteristic-control."
            raise ValueError(msg)

        if values["q_max_ue"] is None:
            msg = "q_max_ue must be specified for Q(U)-characteristic-control."
            raise ValueError(msg)

        if values["m_tg_2015"] is None and values["m_tg_2018"] is None:
            raise Exceptions.QUSlopeNotSpecifiedError

        return values


class ControlQP(ControlBase):
    control_strategy = ControlStrategy.Q_P
    # Q(P) characteristic control mode
    q_p_characteristic_name: str
    q_max_ue: float | None = pydantic.Field(None, ge=0)  # Under excited limit of Q: absolut value
    q_max_oe: float | None = pydantic.Field(None, ge=0)  # Over excited limit of Q: absolut value

    @pydantic.root_validator()
    def validate_q_p_controller(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["q_p_characteristic_name"] is None:
            raise Exceptions.QPCharNotSpecifiedError

        return values


class Exceptions:
    class USetNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("u_set must be specified for U-constant-control.")

    class UMeasRefNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("u_meas_ref must be specified for U-constant-control.")

    class PThresholdUeNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("p_threshold_ue must be specified for cosphi(P)-control.")

    class PThresholdOeNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("p_threshold_oe must be specified for cosphi(P)-control.")

    class UThresholdUeNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("u_threshold_ue must be specified for cosphi(U)-control.")

    class UThresholdOeNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("u_threshold_oe must be specified for cosphi(U)-control.")

    class QSetNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("q_set must be specified for Q-constant-control.")

    class UQ0NotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("u_q0 must be specified for Q(U)-characteristic-control.")

    class UdeadbandUpNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("u_deadband_up must be specified for Q(U)-characteristic-control.")

    class UdeadbandLowNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("u_deadband_low must be specified for Q(U)-characteristic-control.")

    class QUSlopeNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("Either m_tg_2015 or m_tg_2018 must be specified for Q(U)-characteristic-control.")

    class QPCharNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("q_p_characteristic_name must be specified for Q(P)-characteristic-control.")


class Controller(Base):
    controller_type: ControlBase | None = None
    external_controller_name: str | None = None  # if external controller is specified --> name
