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
        cosphi: float
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

    def _is_symmetrical(self, values: tuple[float, ...]) -> bool:
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
    def cosphi(self) -> float:
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
            and self.is_symmetrical_cosphi
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
    def is_symmetrical_cosphi(self) -> bool:
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
            cosphi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cosphi = COSPHI_DEFAULT

        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.Q_CONST,
        }

    @staticmethod
    def calc_pc(
        *,
        pow_act: float,
        cosphi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        try:
            pow_app = abs(pow_act / cosphi)
        except ZeroDivisionError:
            loguru.logger.warning(
                "`cosphi` is 0, but only active power is given. Actual state could not be determined.",
            )
            return {
                "power_apparent": 0,
                "power_active": 0,
                "power_reactive": 0,
                "cosphi": COSPHI_DEFAULT,
                "power_factor_direction": pow_fac_dir,
                "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
            }

        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def calc_ic(
        *,
        voltage: float,
        current: float,
        cosphi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> PowerDict:
        pow_app = abs(voltage * current * scaling) * Exponents.POWER / math.sqrt(3)
        pow_act = math.copysign(pow_app * cosphi, scaling)
        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def calc_sc(
        *,
        pow_app: float,
        cosphi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> PowerDict:
        pow_app = abs(pow_app * scaling) * Exponents.POWER
        pow_act = math.copysign(pow_app * cosphi, scaling)
        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def calc_qc(
        *,
        pow_react: float,
        cosphi: float,
        scaling: float,
    ) -> PowerDict:
        pow_react = pow_react * scaling * Exponents.POWER
        pow_fac_dir = PowerFactorDirection.OE if pow_react < 0 else PowerFactorDirection.UE
        try:
            pow_app = abs(pow_react / math.sin(math.acos(cosphi)))
        except ZeroDivisionError:
            loguru.logger.warning(
                "`cosphi` is 1, but only reactive power is given. Actual state could not be determined.",
            )
            return {
                "power_apparent": 0,
                "power_active": 0,
                "power_reactive": 0,
                "cosphi": COSPHI_DEFAULT,
                "power_factor_direction": pow_fac_dir,
                "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
            }

        pow_act = math.copysign(pow_app * cosphi, scaling)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
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
            cosphi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cosphi = COSPHI_DEFAULT

        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
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
            cosphi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cosphi = COSPHI_DEFAULT

        fac = 1 if pow_fac_dir == PowerFactorDirection.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
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
            cosphi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cosphi = COSPHI_DEFAULT

        pow_fac_dir = PowerFactorDirection.OE if pow_react < 0 else PowerFactorDirection.UE
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "power_factor_direction": pow_fac_dir,
            "power_reactive_control_type": QControlStrategy.COSPHI_CONST,
        }

    @staticmethod
    def get_factors_for_phases(phase_connection_type: PhaseConnectionType) -> tuple[int, int, int, int]:
        if phase_connection_type in (
            PhaseConnectionType.THREE_PH_D,
            PhaseConnectionType.THREE_PH_PH_E,
            PhaseConnectionType.THREE_PH_YN,
        ):
            return (3, 1, 1, 1)
        if phase_connection_type in (
            PhaseConnectionType.TWO_PH_PH_E,
            PhaseConnectionType.TWO_PH_YN,
        ):
            return (2, 1, 1, 0)
        if phase_connection_type in (
            PhaseConnectionType.ONE_PH_PH_E,
            PhaseConnectionType.ONE_PH_PH_N,
            PhaseConnectionType.ONE_PH_PH_PH,
        ):
            return (1, 1, 0, 0)

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
        quot, fac_a, fac_b, fac_c = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_pq(pow_act=pow_act / quot, pow_react=pow_react / quot, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, fac_a=fac_a, fac_b=fac_b, fac_c=fac_c)

    @classmethod
    def from_pc_sym(
        cls,
        *,
        pow_act: float,
        cosphi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, fac_a, fac_b, fac_c = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_pc(pow_act=pow_act / quot, cosphi=cosphi, pow_fac_dir=pow_fac_dir, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, fac_a=fac_a, fac_b=fac_b, fac_c=fac_c)

    @classmethod
    def from_ic_sym(
        cls,
        *,
        voltage: float,
        current: float,
        cosphi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        _, fac_a, fac_b, fac_c = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_ic(
            voltage=voltage,
            current=current,
            cosphi=cosphi,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        return LoadPower.from_power_dict_sym(power_dict=power_dict, fac_a=fac_a, fac_b=fac_b, fac_c=fac_c)

    @classmethod
    def from_sc_sym(
        cls,
        *,
        pow_app: float,
        cosphi: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, fac_a, fac_b, fac_c = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_sc(pow_app=pow_app / quot, cosphi=cosphi, pow_fac_dir=pow_fac_dir, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, fac_a=fac_a, fac_b=fac_b, fac_c=fac_c)

    @classmethod
    def from_qc_sym(
        cls,
        *,
        pow_react: float,
        cosphi: float,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, fac_a, fac_b, fac_c = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_qc(pow_react=pow_react / quot, cosphi=cosphi, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, fac_a=fac_a, fac_b=fac_b, fac_c=fac_c)

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
        quot, fac_a, fac_b, fac_c = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_ip(
            voltage=voltage,
            current=current,
            pow_act=pow_act / quot,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        return LoadPower.from_power_dict_sym(power_dict=power_dict, fac_a=fac_a, fac_b=fac_b, fac_c=fac_c)

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
        quot, fac_a, fac_b, fac_c = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_sp(
            pow_app=pow_app / quot,
            pow_act=pow_act / quot,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        return LoadPower.from_power_dict_sym(power_dict=power_dict, fac_a=fac_a, fac_b=fac_b, fac_c=fac_c)

    @classmethod
    def from_sq_sym(
        cls,
        *,
        pow_app: float,
        pow_react: float,
        scaling: float,
        phase_connection_type: PhaseConnectionType,
    ) -> LoadPower:
        quot, fac_a, fac_b, fac_c = LoadPower.get_factors_for_phases(phase_connection_type)
        power_dict = cls.calc_sq(pow_app=pow_app / quot, pow_react=pow_react / quot, scaling=scaling)
        return LoadPower.from_power_dict_sym(power_dict=power_dict, fac_a=fac_a, fac_b=fac_b, fac_c=fac_c)

    @classmethod
    def from_power_dict_sym(
        cls,
        *,
        power_dict: PowerDict,
        fac_a: int,
        fac_b: int,
        fac_c: int,
    ) -> LoadPower:
        return LoadPower(
            pow_apps=(
                power_dict["power_apparent"] * fac_a,
                power_dict["power_apparent"] * fac_b,
                power_dict["power_apparent"] * fac_c,
            ),
            pow_acts=(
                power_dict["power_active"] * fac_a,
                power_dict["power_active"] * fac_b,
                power_dict["power_active"] * fac_c,
            ),
            pow_reacts=(
                power_dict["power_reactive"] * fac_a,
                power_dict["power_reactive"] * fac_b,
                power_dict["power_reactive"] * fac_c,
            ),
            cos_phis=(power_dict["cosphi"] * fac_a, power_dict["cosphi"] * fac_b, power_dict["cosphi"] * fac_c),
            pow_fac_dir=power_dict["power_factor_direction"],
            pow_react_control_type=power_dict["power_reactive_control_type"],
        )

    @classmethod
    def from_pq_asym(
        cls,
        *,
        pow_act_a: float,
        pow_act_b: float,
        pow_act_c: float,
        pow_react_a: float,
        pow_react_b: float,
        pow_react_c: float,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_pq(pow_act=pow_act_a, pow_react=pow_react_a, scaling=scaling)
        power_dict_b = cls.calc_pq(pow_act=pow_act_b, pow_react=pow_react_b, scaling=scaling)
        power_dict_c = cls.calc_pq(pow_act=pow_act_c, pow_react=pow_react_c, scaling=scaling)
        if not (
            power_dict_a["power_factor_direction"]
            == power_dict_b["power_factor_direction"]
            == power_dict_c["power_factor_direction"]
        ):
            msg = "Cosphi directions do not match."
            raise ValueError(msg)

        pow_fac_dir = power_dict_a["power_factor_direction"]
        return LoadPower(
            pow_apps=(power_dict_a["power_apparent"], power_dict_b["power_apparent"], power_dict_c["power_apparent"]),
            pow_acts=(power_dict_a["power_active"], power_dict_b["power_active"], power_dict_c["power_active"]),
            pow_reacts=(power_dict_a["power_reactive"], power_dict_b["power_reactive"], power_dict_c["power_reactive"]),
            cos_phis=(power_dict_a["cosphi"], power_dict_b["cosphi"], power_dict_c["cosphi"]),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=power_dict_a["power_reactive_control_type"],
        )

    @classmethod
    def from_pc_asym(
        cls,
        *,
        pow_act_a: float,
        pow_act_b: float,
        pow_act_c: float,
        cosphi_a: float,
        cosphi_b: float,
        cosphi_c: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_pc(pow_act=pow_act_a, cosphi=cosphi_a, pow_fac_dir=pow_fac_dir, scaling=scaling)
        power_dict_b = cls.calc_pc(pow_act=pow_act_b, cosphi=cosphi_b, pow_fac_dir=pow_fac_dir, scaling=scaling)
        power_dict_c = cls.calc_pc(pow_act=pow_act_c, cosphi=cosphi_c, pow_fac_dir=pow_fac_dir, scaling=scaling)
        return LoadPower(
            pow_apps=(power_dict_a["power_apparent"], power_dict_b["power_apparent"], power_dict_c["power_apparent"]),
            pow_acts=(power_dict_a["power_active"], power_dict_b["power_active"], power_dict_c["power_active"]),
            pow_reacts=(power_dict_a["power_reactive"], power_dict_b["power_reactive"], power_dict_c["power_reactive"]),
            cos_phis=(power_dict_a["cosphi"], power_dict_b["cosphi"], power_dict_c["cosphi"]),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=power_dict_a["power_reactive_control_type"],
        )

    @classmethod
    def from_ic_asym(
        cls,
        *,
        voltage: float,
        current_a: float,
        current_b: float,
        current_c: float,
        cosphi_a: float,
        cosphi_b: float,
        cosphi_c: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_ic(
            voltage=voltage,
            current=current_a,
            cosphi=cosphi_a,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        power_dict_b = cls.calc_ic(
            voltage=voltage,
            current=current_b,
            cosphi=cosphi_b,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        power_dict_c = cls.calc_ic(
            voltage=voltage,
            current=current_c,
            cosphi=cosphi_c,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        return LoadPower(
            pow_apps=(power_dict_a["power_apparent"], power_dict_b["power_apparent"], power_dict_c["power_apparent"]),
            pow_acts=(power_dict_a["power_active"], power_dict_b["power_active"], power_dict_c["power_active"]),
            pow_reacts=(power_dict_a["power_reactive"], power_dict_b["power_reactive"], power_dict_c["power_reactive"]),
            cos_phis=(power_dict_a["cosphi"], power_dict_b["cosphi"], power_dict_c["cosphi"]),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=power_dict_a["power_reactive_control_type"],
        )

    @classmethod
    def from_sc_asym(
        cls,
        *,
        pow_app_a: float,
        pow_app_b: float,
        pow_app_c: float,
        cosphi_a: float,
        cosphi_b: float,
        cosphi_c: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_sc(pow_app=pow_app_a, cosphi=cosphi_a, pow_fac_dir=pow_fac_dir, scaling=scaling)
        power_dict_b = cls.calc_sc(pow_app=pow_app_b, cosphi=cosphi_b, pow_fac_dir=pow_fac_dir, scaling=scaling)
        power_dict_c = cls.calc_sc(pow_app=pow_app_c, cosphi=cosphi_c, pow_fac_dir=pow_fac_dir, scaling=scaling)
        return LoadPower(
            pow_apps=(power_dict_a["power_apparent"], power_dict_b["power_apparent"], power_dict_c["power_apparent"]),
            pow_acts=(power_dict_a["power_active"], power_dict_b["power_active"], power_dict_c["power_active"]),
            pow_reacts=(power_dict_a["power_reactive"], power_dict_b["power_reactive"], power_dict_c["power_reactive"]),
            cos_phis=(power_dict_a["cosphi"], power_dict_b["cosphi"], power_dict_c["cosphi"]),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=power_dict_a["power_reactive_control_type"],
        )

    @classmethod
    def from_qc_asym(
        cls,
        *,
        pow_react_a: float,
        pow_react_b: float,
        pow_react_c: float,
        cosphi_a: float,
        cosphi_b: float,
        cosphi_c: float,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_qc(pow_react=pow_react_a, cosphi=cosphi_a, scaling=scaling)
        power_dict_b = cls.calc_qc(pow_react=pow_react_b, cosphi=cosphi_b, scaling=scaling)
        power_dict_c = cls.calc_qc(pow_react=pow_react_c, cosphi=cosphi_c, scaling=scaling)
        if not (
            power_dict_a["power_factor_direction"]
            == power_dict_b["power_factor_direction"]
            == power_dict_c["power_factor_direction"]
        ):
            msg = "Cosphi directions do not match."
            raise ValueError(msg)

        pow_fac_dir = power_dict_a["power_factor_direction"]
        return LoadPower(
            pow_apps=(power_dict_a["power_apparent"], power_dict_b["power_apparent"], power_dict_c["power_apparent"]),
            pow_acts=(power_dict_a["power_active"], power_dict_b["power_active"], power_dict_c["power_active"]),
            pow_reacts=(power_dict_a["power_reactive"], power_dict_b["power_reactive"], power_dict_c["power_reactive"]),
            cos_phis=(power_dict_a["cosphi"], power_dict_b["cosphi"], power_dict_c["cosphi"]),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=power_dict_a["power_reactive_control_type"],
        )

    @classmethod
    def from_ip_asym(
        cls,
        *,
        voltage: float,
        current_a: float,
        current_b: float,
        current_c: float,
        pow_act_a: float,
        pow_act_b: float,
        pow_act_c: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_ip(
            voltage=voltage,
            current=current_a,
            pow_act=pow_act_a,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        power_dict_b = cls.calc_ip(
            voltage=voltage,
            current=current_b,
            pow_act=pow_act_b,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        power_dict_c = cls.calc_ip(
            voltage=voltage,
            current=current_c,
            pow_act=pow_act_c,
            pow_fac_dir=pow_fac_dir,
            scaling=scaling,
        )
        return LoadPower(
            pow_apps=(power_dict_a["power_apparent"], power_dict_b["power_apparent"], power_dict_c["power_apparent"]),
            pow_acts=(power_dict_a["power_active"], power_dict_b["power_active"], power_dict_c["power_active"]),
            pow_reacts=(power_dict_a["power_reactive"], power_dict_b["power_reactive"], power_dict_c["power_reactive"]),
            cos_phis=(power_dict_a["cosphi"], power_dict_b["cosphi"], power_dict_c["cosphi"]),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=power_dict_a["power_reactive_control_type"],
        )

    @classmethod
    def from_sp_asym(
        cls,
        *,
        pow_app_a: float,
        pow_app_b: float,
        pow_app_c: float,
        pow_act_a: float,
        pow_act_b: float,
        pow_act_c: float,
        pow_fac_dir: PowerFactorDirection,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_sp(pow_app=pow_app_a, pow_act=pow_act_a, pow_fac_dir=pow_fac_dir, scaling=scaling)
        power_dict_b = cls.calc_sp(pow_app=pow_app_b, pow_act=pow_act_b, pow_fac_dir=pow_fac_dir, scaling=scaling)
        power_dict_c = cls.calc_sp(pow_app=pow_app_c, pow_act=pow_act_c, pow_fac_dir=pow_fac_dir, scaling=scaling)
        return LoadPower(
            pow_apps=(power_dict_a["power_apparent"], power_dict_b["power_apparent"], power_dict_c["power_apparent"]),
            pow_acts=(power_dict_a["power_active"], power_dict_b["power_active"], power_dict_c["power_active"]),
            pow_reacts=(power_dict_a["power_reactive"], power_dict_b["power_reactive"], power_dict_c["power_reactive"]),
            cos_phis=(power_dict_a["cosphi"], power_dict_b["cosphi"], power_dict_c["cosphi"]),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=power_dict_a["power_reactive_control_type"],
        )

    @classmethod
    def from_sq_asym(
        cls,
        *,
        pow_app_a: float,
        pow_app_b: float,
        pow_app_c: float,
        pow_react_a: float,
        pow_react_b: float,
        pow_react_c: float,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_sq(pow_app=pow_app_a, pow_react=pow_react_a, scaling=scaling)
        power_dict_b = cls.calc_sq(pow_app=pow_app_b, pow_react=pow_react_b, scaling=scaling)
        power_dict_c = cls.calc_sq(pow_app=pow_app_c, pow_react=pow_react_c, scaling=scaling)
        if not (
            power_dict_a["power_factor_direction"]
            == power_dict_b["power_factor_direction"]
            == power_dict_c["power_factor_direction"]
        ):
            msg = "Cosphi directions do not match."
            raise ValueError(msg)

        pow_fac_dir = power_dict_a["power_factor_direction"]
        return LoadPower(
            pow_apps=(power_dict_a["power_apparent"], power_dict_b["power_apparent"], power_dict_c["power_apparent"]),
            pow_acts=(power_dict_a["power_active"], power_dict_b["power_active"], power_dict_c["power_active"]),
            pow_reacts=(power_dict_a["power_reactive"], power_dict_b["power_reactive"], power_dict_c["power_reactive"]),
            cos_phis=(power_dict_a["cosphi"], power_dict_b["cosphi"], power_dict_c["cosphi"]),
            pow_fac_dir=pow_fac_dir,
            pow_react_control_type=power_dict_a["power_reactive_control_type"],
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
