# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from enum import Enum

from pydantic import root_validator
from pydantic.class_validators import validator

from powerfactory_utils.schema.base import Base


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


class Exceptions:
    class CosphiNotSpecifiedError(ValueError):
        def __init__(self, ctrl_type: str) -> None:
            super().__init__(f"cosphi must be specified for constant-{ctrl_type}-control.")

    class CosphiTypeNotSpecifiedError(ValueError):
        def __init__(self, ctrl_type: str) -> None:
            super().__init__(f"cosphi_type must be specified for constant-{ctrl_type}-control.")

    class QSetNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("q_set must be specified for Q-setpoint-control.")

    class UQ0NotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("u_q0 must be specified for Q(U)-characteristic-control.")

    class UdeadbandUpNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("udeadband_up must be specified for Q(U)-characteristic-control.")

    class UdeadbandLowNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("udeadband_low must be specified for Q(U)-characteristic-control.")

    class QmaxOENotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("qmax_oe must be specified for Q(U)-characteristic-control.")

    class QmaxUENotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("qmax_ue must be specified for Q(U)-characteristic-control.")

    class TabTarNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("Either m_tab2015 or m_tar2018 must be specified for Q(U)-characteristic-control.")


class Controller(Base):
    controller_type: ControllerType
    external_controller_name: str | None = None  # if external controller is specified --> name
    # cos(phi) control mode
    cosphi_type: CosphiDir | None = None  # CosphiDir
    cosphi: float | None = None  # cos(phi) for calculation of Q in relation to P.
    # q-setpoint control mode
    q_set: float | None = None  # Setpoint of reactive power.
    # Q(U) characteristic control mode
    m_tab2015: float | None = None  # Droop based on VDE-AR-N 4120:2015: '%'-value --> Q = m_% * Pr * dU_kV
    m_tar2018: float | None = None  # Droop based on VDE-AR-N 4120:2018: '%'-value --> Q = m_% * Pr * dU_(% of Un)
    u_q0: float | None = None  # Voltage value, where Q=0: per unit value related to Un
    udeadband_up: float | None = None  # Width of upper deadband (U_1_up - U_Q0): per unit value related to Un
    udeadband_low: float | None = None  # Width of lower deadband (U_Q0 - U_1_low): per unit value related to Un
    qmax_ue: float | None = None  # Over excited limit of Q: absolut per unit value related to Pr
    qmax_oe: float | None = None  # Under excited limit of Q: absolut per unit value related to Pr

    class Config:
        frozen = True

    @validator("cosphi")
    def validate_cosphi(cls, value: float | None) -> float | None:  # noqa: U100
        if value is not None and (not (-1 <= value <= 1)):
            raise ValueError(f"Cosphi must be between -1 and 1, but is {value}.")

        return value

    @validator("qmax_ue")
    def validate_qmax_ue(cls, value: float | None) -> float | None:  # noqa: U100
        if value is not None and (0 > value):
            raise ValueError(
                f"qmax_ue must be greater/equal than 0(p.u.), as it is defined as absolut value, but is {value}."
            )

        return value

    @validator("qmax_oe")
    def validate_qmax_oe(cls, value: float | None) -> float | None:  # noqa: U100
        if value is not None and (0 > value):
            raise ValueError(
                f"qmax_oe must be greater/equal than 0(p.u.), as it is defined as absolut value, but is {value}."
            )

        return value

    @validator("udeadband_up")
    def validate_udeadband_up(cls, value: float | None) -> float | None:  # noqa: U100
        if value is not None and (0 > value):
            raise ValueError(
                f"udeadband_up must be greater/equal than 0(p.u.), as it is defined as absolut value, but is {value}."
            )

        return value

    @validator("udeadband_low")
    def validate_udeadband_low(cls, value: float | None) -> float | None:  # noqa: U100
        if value is not None and (0 > value):
            raise ValueError(
                f"udeadband_low must be greater/equal than 0(p.u.), as it is defined as absolut value, but is {value}."
            )

        return value

    @root_validator()
    def validate_controller_type(cls, controller: Controller) -> Controller:  # noqa: U100
        controller_type = controller.controller_type
        if controller_type == ControllerType.COSPHI_CONST:
            return validate_cosphi_const_controller(controller)

        if controller_type == ControllerType.Q_CONST:
            return validate_q_const_controller(controller)

        if controller_type == ControllerType.Q_U:
            return validate_q_u_controller(controller)

        if controller_type == ControllerType.TANPHI_CONST:
            return validate_tanphi_const_controller(controller)

        return controller


def validate_cosphi_const_controller(controller: Controller) -> Controller:
    if controller.cosphi is None:
        raise Exceptions.CosphiNotSpecifiedError("Cosphi")

    if controller.cosphi_type is None:
        raise Exceptions.CosphiTypeNotSpecifiedError("Cosphi")

    return controller


def validate_q_const_controller(controller: Controller) -> Controller:
    if controller.q_set is None:
        raise Exceptions.QSetNotSpecifiedError

    return controller


def validate_q_u_controller(controller: Controller) -> Controller:
    if controller.u_q0 is None:
        raise Exceptions.UQ0NotSpecifiedError

    if controller.udeadband_up is None:
        raise Exceptions.UdeadbandUpNotSpecifiedError

    if controller.udeadband_low is None:
        raise Exceptions.UdeadbandLowNotSpecifiedError

    if controller.qmax_oe is None:
        raise Exceptions.QmaxOENotSpecifiedError

    if controller.qmax_ue is None:
        raise Exceptions.QmaxUENotSpecifiedError

    if controller.m_tab2015 is None and controller.m_tar2018 is None:
        raise Exceptions.TabTarNotSpecifiedError

    return controller


def validate_tanphi_const_controller(controller: Controller) -> Controller:
    if controller.cosphi is None:
        raise Exceptions.CosphiNotSpecifiedError("Tanphi")

    if controller.cosphi_type is None:
        raise Exceptions.CosphiTypeNotSpecifiedError("Tanphi")

    return controller
