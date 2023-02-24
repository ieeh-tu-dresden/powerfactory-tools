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

    class QUSlopeNotSpecifiedError(ValueError):
        def __init__(self) -> None:
            super().__init__("Either m_tab2015 or m_tar2018 must be specified for Q(U)-characteristic-control.")


class Controller(Base):
    controller_type: ControllerType
    external_controller_name: str | None = None  # if external controller is specified --> name
    # cos(phi) control mode
    cosphi_dir: CosphiDir | None = None  # CosphiDir
    cosphi: float | None = pydantic.Field(None, ge=0, le=1)  # cos(phi) for calculation of Q in relation to P.
    # q-setpoint control mode
    q_set: float | None = None  # Setpoint of reactive power.
    # Q(U) characteristic control mode
    m_tab2015: float | None = None  # Droop/Slope based on VDE-AR-N 4120:2015: '%'-value --> Q = m_% * Pr * dU_kV
    m_tar2018: float | None = None  # Droop/Slope based on VDE-AR-N 4120:2018: '%'-value --> Q = m_% * Pr * dU_(% of Un)
    u_q0: float | None = None  # Voltage value, where Q=0: per unit value related to Un
    udeadband_up: float | None = pydantic.Field(
        None,
        ge=0,
    )  # Width of upper deadband (U_1_up - U_Q0): per unit value related to Un
    udeadband_low: float | None = pydantic.Field(
        None,
        ge=0,
    )  # Width of lower deadband (U_Q0 - U_1_low): per unit value related to Un
    qmax_ue: float | None = pydantic.Field(None, ge=0)  # Over excited limit of Q: absolut value
    qmax_oe: float | None = pydantic.Field(None, ge=0)  # Under excited limit of Q: absolut value

    @pydantic.root_validator()
    def validate_controller_type(cls, values: dict[str, Any]) -> dict[str, Any]:
        controller_type = values["controller_type"]
        if controller_type == ControllerType.COSPHI_CONST:
            return validate_cosphi_const_controller(values)

        if controller_type == ControllerType.Q_CONST:
            return validate_q_const_controller(values)

        if controller_type == ControllerType.Q_U:
            return validate_q_u_controller(values)

        if controller_type == ControllerType.TANPHI_CONST:
            return validate_tanphi_const_controller(values)

        return values


def validate_cosphi_const_controller(values: dict[str, Any]) -> dict[str, Any]:
    if values["cosphi"] is None:
        msg = "cosphi must be specified for constant-cosphi-control."
        raise ValueError(msg)

    if values["cosphi_type"] is None:
        msg = "cosphi_type must be specified for constant-cosphi-control."
        raise ValueError(msg)

    return values


def validate_q_const_controller(values: dict[str, Any]) -> dict[str, Any]:
    if values["q_set"] is None:
        raise Exceptions.QSetNotSpecifiedError

    return values


def validate_q_u_controller(values: dict[str, Any]) -> dict[str, Any]:
    if values["u_q0"] is None:
        raise Exceptions.UQ0NotSpecifiedError

    if values["udeadband_up"] is None:
        raise Exceptions.UdeadbandUpNotSpecifiedError

    if values["udeadband_low"] is None:
        raise Exceptions.UdeadbandLowNotSpecifiedError

    if values["qmax_oe"] is None:
        raise Exceptions.QmaxOENotSpecifiedError

    if values["qmax_ue"] is None:
        raise Exceptions.QmaxUENotSpecifiedError

    if values["m_tab2015"] is None and values["m_tar2018"] is None:
        raise Exceptions.QUSlopeNotSpecifiedError

    return values


def validate_tanphi_const_controller(values: dict[str, Any]) -> dict[str, Any]:
    if values["cosphi"] is None:
        msg = "cosphi must be specified for constant-tanphi-control."
        raise ValueError(msg)

    if values["cosphi_type"] is None:
        msg = "cosphi_type must be specified for constant-tanphi-control."
        raise ValueError(msg)

    return values
