# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import itertools
import math
import typing as t
from dataclasses import dataclass

import loguru
from psdm.steadystate_case.characteristic import Characteristic
from psdm.steadystate_case.controller import ControlCosPhiConst
from psdm.steadystate_case.controller import ControlCosPhiP
from psdm.steadystate_case.controller import ControlCosPhiU
from psdm.steadystate_case.controller import ControlledVoltageRef
from psdm.steadystate_case.controller import ControlPConst
from psdm.steadystate_case.controller import ControlQConst
from psdm.steadystate_case.controller import ControlQP
from psdm.steadystate_case.controller import ControlQU
from psdm.steadystate_case.controller import ControlTanPhiConst
from psdm.steadystate_case.controller import ControlUConst
from psdm.steadystate_case.controller import QControlStrategy
from psdm.topology.load import ActivePower as ActivePowerSet
from psdm.topology.load import Angle
from psdm.topology.load import ApparentPower
from psdm.topology.load import Droop
from psdm.topology.load import Phase
from psdm.topology.load import PhaseConnections
from psdm.topology.load import PhaseConnectionType
from psdm.topology.load import PowerFactor
from psdm.topology.load import PowerFactorDirection
from psdm.topology.load import RatedPower
from psdm.topology.load import ReactivePower as ReactivePowerSet
from psdm.topology.load import Voltage

from powerfactory_tools.constants import DecimalDigits
from powerfactory_tools.constants import Exponents
from powerfactory_tools.powerfactory_types import GeneratorPhaseConnectionType
from powerfactory_tools.powerfactory_types import LoadPhaseConnectionType

if t.TYPE_CHECKING:
    from typing import TypedDict

    class PowerDict(TypedDict):
        power_apparent: float
        power_active: float
        power_reactive: float
        cos_phi: float
        power_factor_direction: PowerFactorDirection
        power_reactive_control_type: QControlStrategy


COSPHI_DEFAULT = 1


LOAD_PHASE_MAPPING = {
    LoadPhaseConnectionType.THREE_PH_D: PhaseConnections(
        values=[
            (Phase.A, Phase.B),
            [Phase.B, Phase.C],
            [Phase.C, Phase.A],
        ],
    ),
    LoadPhaseConnectionType.THREE_PH_PH_E: PhaseConnections(
        values=[
            (Phase.A, Phase.N),
            [Phase.B, Phase.N],
            [Phase.C, Phase.N],
        ],
    ),
    LoadPhaseConnectionType.THREE_PH_YN: PhaseConnections(
        values=[
            (Phase.A, Phase.N),
            [Phase.B, Phase.N],
            [Phase.C, Phase.N],
        ],
    ),
    LoadPhaseConnectionType.TWO_PH_PH_E: PhaseConnections(
        values=[
            (Phase.A, Phase.N),
            [Phase.B, Phase.N],
        ],
    ),
    LoadPhaseConnectionType.TWO_PH_YN: PhaseConnections(
        values=[
            (Phase.A, Phase.N),
            [Phase.B, Phase.N],
        ],
    ),
    LoadPhaseConnectionType.ONE_PH_PH_PH: PhaseConnections(
        values=[
            (Phase.A, Phase.B),
        ],
    ),
    LoadPhaseConnectionType.ONE_PH_PH_N: PhaseConnections(
        values=[
            (Phase.A, Phase.N),
        ],
    ),
    LoadPhaseConnectionType.ONE_PH_PH_E: PhaseConnections(
        values=[
            (Phase.A, Phase.N),
        ],
    ),
}

GENERATOR_PHASE_MAPPING = {
    GeneratorPhaseConnectionType.THREE_PH_D: PhaseConnections(
        values=[
            (Phase.A, Phase.B),
            [Phase.B, Phase.C],
            [Phase.C, Phase.A],
        ],
    ),
    GeneratorPhaseConnectionType.THREE_PH_PH_E: PhaseConnections(
        values=[
            (Phase.A, Phase.N),
            [Phase.B, Phase.N],
            [Phase.C, Phase.N],
        ],
    ),
    GeneratorPhaseConnectionType.ONE_PH_PH_PH: PhaseConnections(
        values=[
            (Phase.A, Phase.B),
        ],
    ),
    GeneratorPhaseConnectionType.ONE_PH_PH_N: PhaseConnections(
        values=[
            (Phase.A, Phase.N),
        ],
    ),
    GeneratorPhaseConnectionType.ONE_PH_PH_E: PhaseConnections(
        values=[
            (Phase.A, Phase.N),
        ],
    ),
}


def _sym_three_phase_no_power(value: float) -> tuple[float, float, float]:
    return (value, value, value)


def _sym_three_phase_power(value: float) -> tuple[float, float, float]:
    return (value / 3, value / 3, value / 3)


def create_sym_three_phase_angle(value: float) -> Angle:
    values = _sym_three_phase_no_power(value)
    return Angle(
        values=[round(v, DecimalDigits.ANGLE) for v in values],
    )


def create_sym_three_phase_active_power(value: float) -> ActivePowerSet:
    values = _sym_three_phase_power(value)
    return ActivePowerSet(
        values=[round(v, DecimalDigits.POWER) for v in values],
    )


def create_sym_three_phase_droop(value: float) -> Droop:
    values = _sym_three_phase_no_power(value)
    return Droop(
        values=[round(v, DecimalDigits.PU) for v in values],
    )


def create_sym_three_phase_power_factor(value: float) -> PowerFactor:
    values = _sym_three_phase_no_power(value)
    return PowerFactor(
        values=[round(v, DecimalDigits.POWERFACTOR) for v in values],
    )


def create_sym_three_phase_reactive_power(value: float) -> ReactivePowerSet:
    values = _sym_three_phase_power(value)
    return ReactivePowerSet(
        values=[round(v, DecimalDigits.POWER) for v in values],
    )


def create_sym_three_phase_voltage(value: float) -> Voltage:
    values = _sym_three_phase_no_power(value)
    return Voltage(
        values=[round(v, DecimalDigits.VOLTAGE) for v in values],
    )


@dataclass
class LoadPower:
    pow_apps: tuple[float, ...]
    pow_acts: tuple[float, ...]
    pow_reacts: tuple[float, ...]
    cos_phis: tuple[float, ...]
    pow_fac_dir: PowerFactorDirection
    pow_react_control_type: QControlStrategy

    @staticmethod
    def _is_symmetrical(values: tuple[float, ...]) -> bool:
        return len(list(itertools.groupby(values))) in (0, 1)

    @property
    def pow_app(self) -> float:
        return sum(self.pow_apps)

    @property
    def pow_app_abs(self) -> float:
        return sum(abs(e) for e in self.pow_apps)

    @property
    def pow_act(self) -> float:
        return sum(self.pow_acts)

    @property
    def pow_react(self) -> float:
        return sum(self.pow_reacts)

    @property
    def cos_phi(self) -> float:
        pow_act = sum(pow_app * cos_phi for pow_app, cos_phi in zip(self.pow_apps, self.cos_phis, strict=True))
        try:
            return abs(pow_act / self.pow_app)
        except ZeroDivisionError:
            return COSPHI_DEFAULT

    @property
    def is_symmetrical(self) -> bool:
        return (
            self.is_symmetrical_app
            and self.is_symmetrical_act
            and self.is_symmetrical_react
            and self.is_symmetrical_cos_phi
        )

    @property
    def is_symmetrical_app(self) -> bool:
        return self._is_symmetrical(self.pow_apps)

    @property
    def is_symmetrical_act(self) -> bool:
        return self._is_symmetrical(self.pow_acts)

    @property
    def is_symmetrical_react(self) -> bool:
        return self._is_symmetrical(self.pow_reacts)

    @property
    def is_symmetrical_cos_phi(self) -> bool:
        return self._is_symmetrical(self.cos_phis)

    @property
    def is_empty(self) -> bool:
        return len(self.pow_apps) == 0

    @staticmethod
    def calc_pq(
        *,
        pow_act: float,
        pow_react: float,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        pow_react = pow_react * scaling * Exponents.POWER
        pow_fac_dir = PowerFactorDirection.OE if pow_react < 0 else PowerFactorDirection.UE
        pow_app = math.sqrt(pow_act**2 + pow_react**2)
        try:
            cos_phi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cos_phi = COSPHI_DEFAULT

        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cos_phi": cos_phi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.Q_CONST,
        }

    @staticmethod
    def calc_pc(
        *,
        pow_act: float,
        cos_phi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        try:
            pow_app = abs(pow_act / cos_phi)
        except ZeroDivisionError:
            loguru.logger.warning(
                "`cos_phi` is 0, but only active power is given. Actual state could not be determined.",
            )
            return {
                "power_apparent": 0,
                "power_active": 0,
                "power_reactive": 0,
                "cos_phi": COSPHI_DEFAULT,
                "power_factor_direction": pow_fac_dir,
                "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
            }

        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cos_phi": cos_phi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def calc_ic(
        *,
        voltage: float,
        current: float,
        cos_phi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> PowerDict:
        pow_app = abs(voltage * current * scaling) * Exponents.POWER / math.sqrt(3)
        pow_act = math.copysign(pow_app * cos_phi, scaling)
        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cos_phi": cos_phi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def calc_sc(
        *,
        pow_app: float,
        cos_phi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> PowerDict:
        pow_app = abs(pow_app * scaling) * Exponents.POWER
        pow_act = math.copysign(pow_app * cos_phi, scaling)
        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cos_phi": cos_phi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def calc_qc(
        *,
        pow_react: float,
        cos_phi: float,
        scaling: float,
    ) -> PowerDict:
        pow_react = pow_react * scaling * Exponents.POWER
        pow_fac_dir = PowerFactorDirection.OE if pow_react < 0 else PowerFactorDirection.UE
        try:
            pow_app = abs(pow_react / math.sin(math.acos(cos_phi)))
        except ZeroDivisionError:
            loguru.logger.warning(
                "`cos_phi` is 1, but only reactive power is given. Actual state could not be determined.",
            )
            return {
                "power_apparent": 0,
                "power_active": 0,
                "power_reactive": 0,
                "cos_phi": COSPHI_DEFAULT,
                "power_factor_direction": pow_fac_dir,
                "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
            }

        pow_act = math.copysign(pow_app * cos_phi, scaling)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cos_phi": cos_phi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def calc_ip(
        *,
        voltage: float,
        current: float,
        pow_act: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        pow_app = abs(voltage * current * scaling) * Exponents.POWER / math.sqrt(3)
        try:
            cos_phi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cos_phi = COSPHI_DEFAULT

        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cos_phi": cos_phi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def calc_sp(
        *,
        pow_app: float,
        pow_act: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> PowerDict:
        pow_app = abs(pow_app * scaling) * Exponents.POWER
        pow_act = pow_act * scaling * Exponents.POWER
        try:
            cos_phi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cos_phi = COSPHI_DEFAULT

        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cos_phi": cos_phi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def calc_sq(
        *,
        pow_app: float,
        pow_react: float,
        scaling: float,
    ) -> PowerDict:
        pow_app = abs(pow_app * scaling) * Exponents.POWER
        pow_react = pow_react * scaling * Exponents.POWER
        pow_act = math.copysign(math.sqrt(pow_app**2 - pow_react**2), scaling)
        try:
            cos_phi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cos_phi = COSPHI_DEFAULT

        pow_fac_dir = PowerFactorDirection.OE if pow_react < 0 else PowerFactorDirection.UE
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cos_phi": cos_phi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def get_factors_for_phases(phase_connection_type: PhaseConnectionType) -> tuple[int, tuple[int, ...]]:
        if phase_connection_type in (
            PhaseConnectionType.THREE_PH_D,
            PhaseConnectionType.THREE_PH_PH_E,
            PhaseConnectionType.THREE_PH_YN,
        ):
            return (3, (1, 1, 1))
        if phase_connection_type in (
            PhaseConnectionType.TWO_PH_PH_E,
            PhaseConnectionType.TWO_PH_YN,
        ):
            return (2, (1, 1))
        if phase_connection_type in (
            PhaseConnectionType.ONE_PH_PH_E,
            PhaseConnectionType.ONE_PH_PH_N,
            PhaseConnectionType.ONE_PH_PH_PH,
        ):
            return (1, (1,))

        msg = "unreachable"
        raise RuntimeError(msg)

    @classmethod
    def from_pq_sym(
        cls,
        *,
        pow_act: float,
        pow_react: float,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, factors = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_pq(pow_act=pow_act / quot, pow_react=pow_react / quot, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, factors=factors)

    @classmethod
    def from_pc_sym(
        cls,
        *,
        pow_act: float,
        cos_phi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, factors = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_pc(pow_act=pow_act / quot, cos_phi=cos_phi, pow_fac_dir=pow_fac_dir, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, factors=factors)

    @classmethod
    def from_ic_sym(
        cls,
        *,
        voltage: float,
        current: float,
        cos_phi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        _, factors = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_ic(
            voltage=voltage,
            current=current,
            cos_phi=cos_phi,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        return LoadPower.from_power_dict_sym(power_dict=power_dict, factors=factors)

    @classmethod
    def from_sc_sym(
        cls,
        *,
        pow_app: float,
        cos_phi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, factors = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_sc(pow_app=pow_app / quot, cos_phi=cos_phi, pow_fac_dir=pow_fac_dir, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, factors=factors)

    @classmethod
    def from_qc_sym(
        cls,
        *,
        pow_react: float,
        cos_phi: float,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, factors = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_qc(pow_react=pow_react / quot, cos_phi=cos_phi, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, factors=factors)

    @classmethod
    def from_ip_sym(
        cls,
        *,
        voltage: float,
        current: float,
        pow_act: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, factors = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_ip(
            voltage=voltage,
            current=current,
            pow_act=pow_act / quot,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        return LoadPower.from_power_dict_sym(power_dict=power_dict, factors=factors)

    @classmethod
    def from_sp_sym(
        cls,
        *,
        pow_app: float,
        pow_act: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, factors = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_sp(
            pow_app=pow_app / quot,
            pow_act=pow_act / quot,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        return LoadPower.from_power_dict_sym(power_dict=power_dict, factors=factors)

    @classmethod
    def from_sq_sym(
        cls,
        *,
        pow_app: float,
        pow_react: float,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, factors = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_sq(pow_app=pow_app / quot, pow_react=pow_react / quot, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, factors=factors)

    @classmethod
    def from_power_dict_sym(
        cls,
        *,
        power_dict: PowerDict,
        factors: tuple[int, ...],
    ) -> LoadPower:
        return LoadPower(
            pow_apps=tuple(power_dict["power_apparent"] * e for e in factors),
            pow_acts=tuple(power_dict["power_active"] * e for e in factors),
            pow_reacts=tuple(power_dict["power_reactive"] * e for e in factors),
            cos_phis=tuple(power_dict["cos_phi"] * e for e in factors),
            pow_fac_dir=power_dict["power_factor_direction"],
            pow_react_control_type=power_dict["power_reactive_control_type"],
        )

    @classmethod
    def from_pq_asym(
        cls,
        *,
        pow_acts: tuple[float, ...],
        pow_reacts: tuple[float, ...],
        scaling: float,
    ) -> LoadPower:
        power_dicts = tuple(
            cls.calc_pq(pow_act=pow_act, pow_react=pow_react, scaling=scaling)
            for pow_act, pow_react in zip(pow_acts, pow_reacts, strict=True)
        )
        if not cls._is_symmetrical(values=tuple(e["power_factor_direction"] for e in power_dicts)):
            msg = "CosPhi directions do not match."
            raise ValueError(msg)

        pow_fac_dir = power_dicts[0]["power_factor_direction"]
        pow_react_control_type = power_dicts[0]["power_reactive_control_type"]
        return LoadPower(
            pow_apps=tuple(e["power_apparent"] for e in power_dicts),
            pow_acts=tuple(e["power_active"] for e in power_dicts),
            pow_reacts=tuple(e["power_reactive"] for e in power_dicts),
            cos_phis=tuple(e["cos_phi"] for e in power_dicts),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=pow_react_control_type,
        )

    @classmethod
    def from_pc_asym(
        cls,
        *,
        pow_acts: tuple[float, ...],
        cos_phis: tuple[float, ...],
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dicts = tuple(
            cls.calc_pc(pow_act=pow_act, cos_phi=cos_phi, pow_fac_dir=pow_fac_dir, scaling=scaling)
            for pow_act, cos_phi in zip(pow_acts, cos_phis, strict=True)
        )
        pow_react_control_type = power_dicts[0]["power_reactive_control_type"]
        return LoadPower(
            pow_apps=tuple(e["power_apparent"] for e in power_dicts),
            pow_acts=tuple(e["power_active"] for e in power_dicts),
            pow_reacts=tuple(e["power_reactive"] for e in power_dicts),
            cos_phis=tuple(e["cos_phi"] for e in power_dicts),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=pow_react_control_type,
        )

    @classmethod
    def from_ic_asym(
        cls,
        *,
        voltage: float,
        currents: tuple[float, ...],
        cos_phis: tuple[float, ...],
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dicts = tuple(
            cls.calc_ic(voltage=voltage, current=current, cos_phi=cos_phi, pow_fac_dir=pow_fac_dir, scaling=scaling)
            for current, cos_phi in zip(currents, cos_phis, strict=True)
        )
        pow_react_control_type = power_dicts[0]["power_reactive_control_type"]
        return LoadPower(
            pow_apps=tuple(e["power_apparent"] for e in power_dicts),
            pow_acts=tuple(e["power_active"] for e in power_dicts),
            pow_reacts=tuple(e["power_reactive"] for e in power_dicts),
            cos_phis=tuple(e["cos_phi"] for e in power_dicts),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=pow_react_control_type,
        )

    @classmethod
    def from_sc_asym(
        cls,
        *,
        pow_apps: tuple[float, ...],
        cos_phis: tuple[float, ...],
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dicts = tuple(
            cls.calc_sc(pow_app=pow_app, cos_phi=cos_phi, pow_fac_dir=pow_fac_dir, scaling=scaling)
            for pow_app, cos_phi in zip(pow_apps, cos_phis, strict=True)
        )
        pow_react_control_type = power_dicts[0]["power_reactive_control_type"]
        return LoadPower(
            pow_apps=tuple(e["power_apparent"] for e in power_dicts),
            pow_acts=tuple(e["power_active"] for e in power_dicts),
            pow_reacts=tuple(e["power_reactive"] for e in power_dicts),
            cos_phis=tuple(e["cos_phi"] for e in power_dicts),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=pow_react_control_type,
        )

    @classmethod
    def from_qc_asym(
        cls,
        *,
        pow_reacts: tuple[float, ...],
        cos_phis: tuple[float, ...],
        scaling: float,
    ) -> LoadPower:
        power_dicts = tuple(
            cls.calc_qc(pow_react=pow_react, cos_phi=cos_phi, scaling=scaling)
            for pow_react, cos_phi in zip(pow_reacts, cos_phis, strict=True)
        )
        if not cls._is_symmetrical(values=tuple(e["power_factor_direction"] for e in power_dicts)):
            msg = "CosPhi directions do not match."
            raise ValueError(msg)

        pow_fac_dir = power_dicts[0]["power_factor_direction"]
        pow_react_control_type = power_dicts[0]["power_reactive_control_type"]
        return LoadPower(
            pow_apps=tuple(e["power_apparent"] for e in power_dicts),
            pow_acts=tuple(e["power_active"] for e in power_dicts),
            pow_reacts=tuple(e["power_reactive"] for e in power_dicts),
            cos_phis=tuple(e["cos_phi"] for e in power_dicts),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=pow_react_control_type,
        )

    @classmethod
    def from_ip_asym(
        cls,
        *,
        voltage: float,
        currents: tuple[float, ...],
        pow_acts: tuple[float, ...],
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dicts = tuple(
            cls.calc_ip(voltage=voltage, current=current, pow_act=pow_act, pow_fac_dir=pow_fac_dir, scaling=scaling)
            for current, pow_act in zip(currents, pow_acts, strict=True)
        )
        pow_react_control_type = power_dicts[0]["power_reactive_control_type"]
        return LoadPower(
            pow_apps=tuple(e["power_apparent"] for e in power_dicts),
            pow_acts=tuple(e["power_active"] for e in power_dicts),
            pow_reacts=tuple(e["power_reactive"] for e in power_dicts),
            cos_phis=tuple(e["cos_phi"] for e in power_dicts),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=pow_react_control_type,
        )

    @classmethod
    def from_sp_asym(
        cls,
        *,
        pow_apps: tuple[float, ...],
        pow_acts: tuple[float, ...],
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dicts = tuple(
            cls.calc_sp(pow_app=pow_app, pow_act=pow_act, pow_fac_dir=pow_fac_dir, scaling=scaling)
            for pow_app, pow_act in zip(pow_apps, pow_acts, strict=True)
        )
        pow_react_control_type = power_dicts[0]["power_reactive_control_type"]
        return LoadPower(
            pow_apps=tuple(e["power_apparent"] for e in power_dicts),
            pow_acts=tuple(e["power_active"] for e in power_dicts),
            pow_reacts=tuple(e["power_reactive"] for e in power_dicts),
            cos_phis=tuple(e["cos_phi"] for e in power_dicts),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=pow_react_control_type,
        )

    @classmethod
    def from_sq_asym(
        cls,
        *,
        pow_apps: tuple[float, ...],
        pow_reacts: tuple[float, ...],
        scaling: float,
    ) -> LoadPower:
        power_dicts = tuple(
            cls.calc_sq(pow_app=pow_app, pow_react=pow_react, scaling=scaling)
            for pow_app, pow_react in zip(pow_apps, pow_reacts, strict=True)
        )
        if not cls._is_symmetrical(values=tuple(e["power_factor_direction"] for e in power_dicts)):
            msg = "CosPhi directions do not match."
            raise ValueError(msg)

        pow_fac_dir = power_dicts[0]["power_factor_direction"]
        pow_react_control_type = power_dicts[0]["power_reactive_control_type"]
        return LoadPower(
            pow_apps=tuple(e["power_apparent"] for e in power_dicts),
            pow_acts=tuple(e["power_active"] for e in power_dicts),
            pow_reacts=tuple(e["power_reactive"] for e in power_dicts),
            cos_phis=tuple(e["cos_phi"] for e in power_dicts),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=pow_react_control_type,
        )

    def as_active_power_ssc(self) -> ActivePowerSet:
        return ActivePowerSet(values=(round(e, DecimalDigits.POWER + 2) for e in self.pow_acts))

    def as_reactive_power_ssc(self) -> ReactivePowerSet:
        # remark: actual reactive power indirectly (Q(U); Q(P)) set by external controller is not shown in ReactivePower
        return ReactivePowerSet(values=(round(e, DecimalDigits.POWER + 2) for e in self.pow_reacts))

    def as_rated_power(self) -> RatedPower:
        pow_apps = ApparentPower(values=(round(e, DecimalDigits.POWER + 2) for e in self.pow_apps))
        cos_phis = PowerFactor(values=(round(e, DecimalDigits.POWERFACTOR) for e in self.cos_phis))
        return RatedPower.from_apparent_power(pow_apps, cos_phis)

    def limit_phases(self, n_phases: int) -> LoadPower:
        return LoadPower(
            pow_apps=self.pow_apps[:n_phases],
            pow_acts=self.pow_acts[:n_phases],
            pow_reacts=self.pow_reacts[:n_phases],
            cos_phis=self.cos_phis[:n_phases],
            pow_fac_dir=self.pow_fac_dir,
            pow_react_control_type=self.pow_react_control_type,
        )


@dataclass
class ControlType:
    @staticmethod
    def create_p_const(power: LoadPower) -> ControlPConst:
        return ControlPConst(
            p_set=power.as_active_power_ssc(),
        )

    @staticmethod
    def create_q_const(power: LoadPower) -> ControlQConst:
        return ControlQConst(
            q_set=power.as_reactive_power_ssc(),
        )

    @staticmethod
    def create_cos_phi_const(power: LoadPower) -> ControlCosPhiConst:
        return ControlCosPhiConst(
            cos_phi_set=PowerFactor(
                values=(round(e, DecimalDigits.POWERFACTOR) for e in power.cos_phis),
                direction=power.pow_fac_dir,
            ),
        )

    @staticmethod
    def create_tan_phi_const(power: LoadPower) -> ControlTanPhiConst:
        return ControlTanPhiConst(
            tan_phi_set=PowerFactor(
                values=(round(math.tan(math.acos(e)), DecimalDigits.POWERFACTOR) for e in power.cos_phis),
                direction=power.pow_fac_dir,
            ),
        )

    @staticmethod
    def create_q_u_sym(
        droop_up: float,
        droop_low: float,
        u_q0: float,
        u_deadband_up: float,
        u_deadband_low: float,
        q_max_ue: float,
        q_max_oe: float,
    ) -> ControlQU:
        return ControlQU(
            droop_up=create_sym_three_phase_droop(droop_up),
            droop_low=create_sym_three_phase_droop(droop_low),
            u_q0=create_sym_three_phase_voltage(u_q0),
            u_deadband_low=create_sym_three_phase_voltage(u_deadband_low),
            u_deadband_up=create_sym_three_phase_voltage(u_deadband_up),
            q_max_ue=create_sym_three_phase_reactive_power(q_max_ue),
            q_max_oe=create_sym_three_phase_reactive_power(q_max_oe),
        )

    @staticmethod
    def create_cos_phi_p_sym(
        cos_phi_ue: float,
        cos_phi_oe: float,
        p_threshold_ue: float,
        p_threshold_oe: float,
    ) -> ControlCosPhiP:
        return ControlCosPhiP(
            cos_phi_ue=create_sym_three_phase_power_factor(cos_phi_ue),
            cos_phi_oe=create_sym_three_phase_power_factor(cos_phi_oe),
            p_threshold_ue=create_sym_three_phase_active_power(p_threshold_ue),
            p_threshold_oe=create_sym_three_phase_active_power(p_threshold_oe),
        )

    @staticmethod
    def create_cos_phi_u_sym(
        cos_phi_ue: float,
        cos_phi_oe: float,
        u_threshold_ue: float,
        u_threshold_oe: float,
    ) -> ControlCosPhiU:
        return ControlCosPhiU(
            cos_phi_ue=create_sym_three_phase_power_factor(cos_phi_ue),
            cos_phi_oe=create_sym_three_phase_power_factor(cos_phi_oe),
            u_threshold_ue=create_sym_three_phase_voltage(u_threshold_ue),
            u_threshold_oe=create_sym_three_phase_voltage(u_threshold_oe),
        )

    @staticmethod
    def create_q_p_sym(
        q_p_characteristic_name: Characteristic,
        q_max_ue: float | None,
        q_max_oe: float | None,
    ) -> ControlQP:
        if q_max_ue is not None:
            q_max_ue = create_sym_three_phase_reactive_power(q_max_ue)
        if q_max_oe is not None:
            q_max_oe = create_sym_three_phase_reactive_power(q_max_oe)
        return ControlQP(
            q_p_characteristic=Characteristic(name=q_p_characteristic_name),
            q_max_ue=q_max_ue,
            q_max_oe=q_max_oe,
        )

    @staticmethod
    def create_u_const_sym(
        u_set: float,
        u_meas_ref: ControlledVoltageRef | None = None,
    ) -> ControlUConst:
        if u_meas_ref is not None:
            return ControlUConst(
                u_set=create_sym_three_phase_voltage(u_set),
                u_meas_ref=u_meas_ref,
            )
        return ControlUConst(u_set=create_sym_three_phase_voltage(u_set))

    @staticmethod
    def transform_qu_slope(
        *,
        value: float,
        given_format: t.Literal["2015", "2018"],
        target_format: t.Literal["2015", "2018"],
        u_n: float,
    ) -> float:
        """Transform slope of Q(U)-characteristic from given format type to another format type.

        Arguments:
            value {float} -- slope of Q(U)-characteristic
            given_format {str} -- format specifier for related normative guideline (e.g. '2015' or '2018')
            target_format {str} -- format specifier for related normative guideline (e.g. '2015' or '2018')
            u_n {float} -- nominal voltage of the related controller, in V

        Returns:
            float -- transformed slope
        """
        if given_format == "2015" and target_format == "2018":
            return value / (1e3 / u_n * 100)  # 2018: (% von Pr) / (p.u. von Un)

        if given_format == "2018" and target_format == "2015":
            return value * (1e3 / u_n * 100)  # 2015: (% von Pr) / kV

        msg = "unreachable"
        raise RuntimeError(msg)
