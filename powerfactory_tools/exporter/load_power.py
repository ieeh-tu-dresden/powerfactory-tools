# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_tools.constants import DecimalDigits
from powerfactory_tools.constants import Exponents
from powerfactory_tools.schema.base import CosphiDir
from powerfactory_tools.schema.steadystate_case.active_power import ActivePower
from powerfactory_tools.schema.steadystate_case.reactive_power import ReactivePower
from powerfactory_tools.schema.topology.load import RatedPower

if TYPE_CHECKING:
    from typing import TypedDict

    from powerfactory_tools.schema.steadystate_case.controller import Controller

    class PowerDict(TypedDict):
        power_apparent: float
        power_active: float
        power_reactive: float
        cosphi: float
        cosphi_dir: CosphiDir


COSPHI_DEFAULT = 1


@dataclass
class LoadPower:
    pow_app_a: float
    pow_app_b: float
    pow_app_c: float
    pow_act_a: float
    pow_act_b: float
    pow_act_c: float
    pow_react_a: float
    pow_react_b: float
    pow_react_c: float
    cosphi_a: float
    cosphi_b: float
    cosphi_c: float
    cosphi_dir: CosphiDir

    @property
    def pow_app(self) -> float:
        return self.pow_app_a + self.pow_app_b + self.pow_app_c

    @property
    def pow_app_abs(self) -> float:
        return abs(self.pow_app_a) + abs(self.pow_app_b) + abs(self.pow_app_c)

    @property
    def pow_act(self) -> float:
        return self.pow_act_a + self.pow_act_b + self.pow_act_c

    @property
    def pow_react(self) -> float:
        return self.pow_react_a + self.pow_react_b + self.pow_react_c

    @property
    def cosphi(self) -> float:
        pow_act = self.pow_app_a * self.cosphi_a + self.pow_app_b * self.cosphi_b + self.pow_app_c * self.cosphi_c
        try:
            return abs(pow_act / self.pow_app)
        except ZeroDivisionError:
            return COSPHI_DEFAULT

    @property
    def is_symmetrical(self) -> bool:
        return self.is_symmetrical_s and self.is_symmetrical_p and self.is_symmetrical_q and self.is_symmetrical_cosphi

    @property
    def is_symmetrical_s(self) -> bool:
        return self.pow_app_a == self.pow_app_b == self.pow_app_c

    @property
    def is_symmetrical_p(self) -> bool:
        return self.pow_act_a == self.pow_act_b == self.pow_act_c

    @property
    def is_symmetrical_q(self) -> bool:
        return self.pow_react_a == self.pow_react_b == self.pow_react_c

    @property
    def is_symmetrical_cosphi(self) -> bool:
        return self.cosphi_a == self.cosphi_b == self.cosphi_c

    @property
    def is_empty(self) -> bool:
        return self.pow_app_a == 0

    @staticmethod
    def calc_pq(
        *,
        pow_act: float,
        pow_react: float,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        pow_react = pow_react * scaling * Exponents.POWER
        cosphi_dir = CosphiDir.OE if pow_react < 0 else CosphiDir.UE
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
            "cosphi_dir": cosphi_dir,
        }

    @staticmethod
    def calc_pc(
        *,
        pow_act: float,
        cosphi: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        try:
            pow_app = abs(pow_act / cosphi)
        except ZeroDivisionError:
            logger.warning("`cosphi` is 0, but only active power is given. Actual state could not be determined.")
            return {
                "power_apparent": 0,
                "power_active": 0,
                "power_reactive": 0,
                "cosphi": COSPHI_DEFAULT,
                "cosphi_dir": cosphi_dir,
            }

        fac = 1 if cosphi_dir == CosphiDir.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "cosphi_dir": cosphi_dir,
        }

    @staticmethod
    def calc_ic(
        *,
        voltage: float,
        current: float,
        cosphi: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> PowerDict:
        pow_app = abs(voltage * current * scaling) * Exponents.POWER / math.sqrt(3)
        pow_act = pow_app * cosphi
        fac = 1 if cosphi_dir == CosphiDir.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "cosphi_dir": cosphi_dir,
        }

    @staticmethod
    def calc_sc(
        *,
        pow_app: float,
        cosphi: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> PowerDict:
        pow_app = abs(pow_app * scaling) * Exponents.POWER
        pow_act = pow_app * cosphi
        fac = 1 if cosphi_dir == CosphiDir.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "cosphi_dir": cosphi_dir,
        }

    @staticmethod
    def calc_qc(
        *,
        pow_react: float,
        cosphi: float,
        scaling: float,
    ) -> PowerDict:
        pow_react = pow_react * scaling * Exponents.POWER
        cosphi_dir = CosphiDir.OE if pow_react < 0 else CosphiDir.UE
        try:
            pow_app = abs(pow_react / math.sin(math.acos(cosphi)))
        except ZeroDivisionError:
            logger.warning("`cosphi` is 1, but only reactive power is given. Actual state could not be determined.")
            return {
                "power_apparent": 0,
                "power_active": 0,
                "power_reactive": 0,
                "cosphi": COSPHI_DEFAULT,
                "cosphi_dir": cosphi_dir,
            }

        pow_act = pow_app * cosphi
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "cosphi_dir": cosphi_dir,
        }

    @staticmethod
    def calc_ip(
        *,
        voltage: float,
        current: float,
        pow_act: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        pow_app = abs(voltage * current * scaling) * Exponents.POWER / math.sqrt(3)
        try:
            cosphi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cosphi = COSPHI_DEFAULT

        fac = 1 if cosphi_dir == CosphiDir.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "cosphi_dir": cosphi_dir,
        }

    @staticmethod
    def calc_sp(
        *,
        pow_app: float,
        pow_act: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> PowerDict:
        pow_app = abs(pow_app * scaling) * Exponents.POWER
        pow_act = pow_act * scaling * Exponents.POWER
        try:
            cosphi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cosphi = COSPHI_DEFAULT

        fac = 1 if cosphi_dir == CosphiDir.UE else -1
        pow_react = fac * math.sqrt(pow_app**2 - pow_act**2)
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "cosphi_dir": cosphi_dir,
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
        pow_act = math.sqrt(pow_app**2 - pow_react**2)
        try:
            cosphi = abs(pow_act / pow_app)
        except ZeroDivisionError:
            cosphi = COSPHI_DEFAULT

        cosphi_dir = CosphiDir.OE if pow_react < 0 else CosphiDir.UE
        return {
            "power_apparent": pow_app,
            "power_active": pow_act,
            "power_reactive": pow_react,
            "cosphi": cosphi,
            "cosphi_dir": cosphi_dir,
        }

    @classmethod
    def from_pq_sym(
        cls,
        *,
        pow_act: float,
        pow_react: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_pq(pow_act=pow_act / 3, pow_react=pow_react / 3, scaling=scaling)
        return LoadPower(
            pow_app_a=power_dict["power_apparent"],
            pow_app_b=power_dict["power_apparent"],
            pow_app_c=power_dict["power_apparent"],
            pow_act_a=power_dict["power_active"],
            pow_act_b=power_dict["power_active"],
            pow_act_c=power_dict["power_active"],
            pow_react_a=power_dict["power_reactive"],
            pow_react_b=power_dict["power_reactive"],
            pow_react_c=power_dict["power_reactive"],
            cosphi_a=power_dict["cosphi"],
            cosphi_b=power_dict["cosphi"],
            cosphi_c=power_dict["cosphi"],
            cosphi_dir=power_dict["cosphi_dir"],
        )

    @classmethod
    def from_pc_sym(
        cls,
        *,
        pow_act: float,
        cosphi: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_pc(pow_act=pow_act / 3, cosphi=cosphi, cosphi_dir=cosphi_dir, scaling=scaling)
        return LoadPower(
            pow_app_a=power_dict["power_apparent"],
            pow_app_b=power_dict["power_apparent"],
            pow_app_c=power_dict["power_apparent"],
            pow_act_a=power_dict["power_active"],
            pow_act_b=power_dict["power_active"],
            pow_act_c=power_dict["power_active"],
            pow_react_a=power_dict["power_reactive"],
            pow_react_b=power_dict["power_reactive"],
            pow_react_c=power_dict["power_reactive"],
            cosphi_a=power_dict["cosphi"],
            cosphi_b=power_dict["cosphi"],
            cosphi_c=power_dict["cosphi"],
            cosphi_dir=cosphi_dir,
        )

    @classmethod
    def from_ic_sym(
        cls,
        *,
        voltage: float,
        current: float,
        cosphi: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_ic(
            voltage=voltage,
            current=current,
            cosphi=cosphi,
            cosphi_dir=cosphi_dir,
            scaling=scaling,
        )
        return LoadPower(
            pow_app_a=power_dict["power_apparent"],
            pow_app_b=power_dict["power_apparent"],
            pow_app_c=power_dict["power_apparent"],
            pow_act_a=power_dict["power_active"],
            pow_act_b=power_dict["power_active"],
            pow_act_c=power_dict["power_active"],
            pow_react_a=power_dict["power_reactive"],
            pow_react_b=power_dict["power_reactive"],
            pow_react_c=power_dict["power_reactive"],
            cosphi_a=power_dict["cosphi"],
            cosphi_b=power_dict["cosphi"],
            cosphi_c=power_dict["cosphi"],
            cosphi_dir=cosphi_dir,
        )

    @classmethod
    def from_sc_sym(
        cls,
        *,
        pow_app: float,
        cosphi: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_sc(pow_app=pow_app / 3, cosphi=cosphi, cosphi_dir=cosphi_dir, scaling=scaling)
        return LoadPower(
            pow_app_a=power_dict["power_apparent"],
            pow_app_b=power_dict["power_apparent"],
            pow_app_c=power_dict["power_apparent"],
            pow_act_a=power_dict["power_active"],
            pow_act_b=power_dict["power_active"],
            pow_act_c=power_dict["power_active"],
            pow_react_a=power_dict["power_reactive"],
            pow_react_b=power_dict["power_reactive"],
            pow_react_c=power_dict["power_reactive"],
            cosphi_a=power_dict["cosphi"],
            cosphi_b=power_dict["cosphi"],
            cosphi_c=power_dict["cosphi"],
            cosphi_dir=cosphi_dir,
        )

    @classmethod
    def from_qc_sym(
        cls,
        *,
        pow_react: float,
        cosphi: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_qc(pow_react=pow_react / 3, cosphi=cosphi, scaling=scaling)
        return LoadPower(
            pow_app_a=power_dict["power_apparent"],
            pow_app_b=power_dict["power_apparent"],
            pow_app_c=power_dict["power_apparent"],
            pow_act_a=power_dict["power_active"],
            pow_act_b=power_dict["power_active"],
            pow_act_c=power_dict["power_active"],
            pow_react_a=power_dict["power_reactive"],
            pow_react_b=power_dict["power_reactive"],
            pow_react_c=power_dict["power_reactive"],
            cosphi_a=power_dict["cosphi"],
            cosphi_b=power_dict["cosphi"],
            cosphi_c=power_dict["cosphi"],
            cosphi_dir=power_dict["cosphi_dir"],
        )

    @classmethod
    def from_ip_sym(
        cls,
        *,
        voltage: float,
        current: float,
        pow_act: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_ip(
            voltage=voltage,
            current=current,
            pow_act=pow_act / 3,
            cosphi_dir=cosphi_dir,
            scaling=scaling,
        )
        return LoadPower(
            pow_app_a=power_dict["power_apparent"],
            pow_app_b=power_dict["power_apparent"],
            pow_app_c=power_dict["power_apparent"],
            pow_act_a=power_dict["power_active"],
            pow_act_b=power_dict["power_active"],
            pow_act_c=power_dict["power_active"],
            pow_react_a=power_dict["power_reactive"],
            pow_react_b=power_dict["power_reactive"],
            pow_react_c=power_dict["power_reactive"],
            cosphi_a=power_dict["cosphi"],
            cosphi_b=power_dict["cosphi"],
            cosphi_c=power_dict["cosphi"],
            cosphi_dir=cosphi_dir,
        )

    @classmethod
    def from_sp_sym(
        cls,
        *,
        pow_app: float,
        pow_act: float,
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_sp(pow_app=pow_app / 3, pow_act=pow_act / 3, cosphi_dir=cosphi_dir, scaling=scaling)
        return LoadPower(
            pow_app_a=power_dict["power_apparent"],
            pow_app_b=power_dict["power_apparent"],
            pow_app_c=power_dict["power_apparent"],
            pow_act_a=power_dict["power_active"],
            pow_act_b=power_dict["power_active"],
            pow_act_c=power_dict["power_active"],
            pow_react_a=power_dict["power_reactive"],
            pow_react_b=power_dict["power_reactive"],
            pow_react_c=power_dict["power_reactive"],
            cosphi_a=power_dict["cosphi"],
            cosphi_b=power_dict["cosphi"],
            cosphi_c=power_dict["cosphi"],
            cosphi_dir=cosphi_dir,
        )

    @classmethod
    def from_sq_sym(
        cls,
        *,
        pow_app: float,
        pow_react: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_sq(pow_app=pow_app / 3, pow_react=pow_react / 3, scaling=scaling)
        return LoadPower(
            pow_app_a=power_dict["power_apparent"],
            pow_app_b=power_dict["power_apparent"],
            pow_app_c=power_dict["power_apparent"],
            pow_act_a=power_dict["power_active"],
            pow_act_b=power_dict["power_active"],
            pow_act_c=power_dict["power_active"],
            pow_react_a=power_dict["power_reactive"],
            pow_react_b=power_dict["power_reactive"],
            pow_react_c=power_dict["power_reactive"],
            cosphi_a=power_dict["cosphi"],
            cosphi_b=power_dict["cosphi"],
            cosphi_c=power_dict["cosphi"],
            cosphi_dir=power_dict["cosphi_dir"],
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
        if not (power_dict_a["cosphi_dir"] == power_dict_b["cosphi_dir"] == power_dict_c["cosphi_dir"]):
            msg = "Cosphi directions do not match."
            raise ValueError(msg)

        cosphi_dir = power_dict_a["cosphi_dir"]
        return LoadPower(
            pow_app_a=power_dict_a["power_apparent"],
            pow_app_b=power_dict_b["power_apparent"],
            pow_app_c=power_dict_c["power_apparent"],
            pow_act_a=power_dict_a["power_active"],
            pow_act_b=power_dict_b["power_active"],
            pow_act_c=power_dict_c["power_active"],
            pow_react_a=power_dict_a["power_reactive"],
            pow_react_b=power_dict_b["power_reactive"],
            pow_react_c=power_dict_c["power_reactive"],
            cosphi_a=power_dict_a["cosphi"],
            cosphi_b=power_dict_b["cosphi"],
            cosphi_c=power_dict_c["cosphi"],
            cosphi_dir=cosphi_dir,
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
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_pc(pow_act=pow_act_a, cosphi=cosphi_a, cosphi_dir=cosphi_dir, scaling=scaling)
        power_dict_b = cls.calc_pc(pow_act=pow_act_b, cosphi=cosphi_b, cosphi_dir=cosphi_dir, scaling=scaling)
        power_dict_c = cls.calc_pc(pow_act=pow_act_c, cosphi=cosphi_c, cosphi_dir=cosphi_dir, scaling=scaling)
        return LoadPower(
            pow_app_a=power_dict_a["power_apparent"],
            pow_app_b=power_dict_b["power_apparent"],
            pow_app_c=power_dict_c["power_apparent"],
            pow_act_a=power_dict_a["power_active"],
            pow_act_b=power_dict_b["power_active"],
            pow_act_c=power_dict_c["power_active"],
            pow_react_a=power_dict_a["power_reactive"],
            pow_react_b=power_dict_b["power_reactive"],
            pow_react_c=power_dict_c["power_reactive"],
            cosphi_a=power_dict_a["cosphi"],
            cosphi_b=power_dict_b["cosphi"],
            cosphi_c=power_dict_c["cosphi"],
            cosphi_dir=cosphi_dir,
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
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_ic(
            voltage=voltage,
            current=current_a,
            cosphi=cosphi_a,
            cosphi_dir=cosphi_dir,
            scaling=scaling,
        )
        power_dict_b = cls.calc_ic(
            voltage=voltage,
            current=current_b,
            cosphi=cosphi_b,
            cosphi_dir=cosphi_dir,
            scaling=scaling,
        )
        power_dict_c = cls.calc_ic(
            voltage=voltage,
            current=current_c,
            cosphi=cosphi_c,
            cosphi_dir=cosphi_dir,
            scaling=scaling,
        )
        return LoadPower(
            pow_app_a=power_dict_a["power_apparent"],
            pow_app_b=power_dict_b["power_apparent"],
            pow_app_c=power_dict_c["power_apparent"],
            pow_act_a=power_dict_a["power_active"],
            pow_act_b=power_dict_b["power_active"],
            pow_act_c=power_dict_c["power_active"],
            pow_react_a=power_dict_a["power_reactive"],
            pow_react_b=power_dict_b["power_reactive"],
            pow_react_c=power_dict_c["power_reactive"],
            cosphi_a=power_dict_a["cosphi"],
            cosphi_b=power_dict_b["cosphi"],
            cosphi_c=power_dict_c["cosphi"],
            cosphi_dir=cosphi_dir,
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
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_sc(pow_app=pow_app_a, cosphi=cosphi_a, cosphi_dir=cosphi_dir, scaling=scaling)
        power_dict_b = cls.calc_sc(pow_app=pow_app_b, cosphi=cosphi_b, cosphi_dir=cosphi_dir, scaling=scaling)
        power_dict_c = cls.calc_sc(pow_app=pow_app_c, cosphi=cosphi_c, cosphi_dir=cosphi_dir, scaling=scaling)
        return LoadPower(
            pow_app_a=power_dict_a["power_apparent"],
            pow_app_b=power_dict_b["power_apparent"],
            pow_app_c=power_dict_c["power_apparent"],
            pow_act_a=power_dict_a["power_active"],
            pow_act_b=power_dict_b["power_active"],
            pow_act_c=power_dict_c["power_active"],
            pow_react_a=power_dict_a["power_reactive"],
            pow_react_b=power_dict_b["power_reactive"],
            pow_react_c=power_dict_c["power_reactive"],
            cosphi_a=power_dict_a["cosphi"],
            cosphi_b=power_dict_b["cosphi"],
            cosphi_c=power_dict_c["cosphi"],
            cosphi_dir=cosphi_dir,
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
        if not (power_dict_a["cosphi_dir"] == power_dict_b["cosphi_dir"] == power_dict_c["cosphi_dir"]):
            msg = "Cosphi directions do not match."
            raise ValueError(msg)

        cosphi_dir = power_dict_a["cosphi_dir"]
        return LoadPower(
            pow_app_a=power_dict_a["power_apparent"],
            pow_app_b=power_dict_b["power_apparent"],
            pow_app_c=power_dict_c["power_apparent"],
            pow_act_a=power_dict_a["power_active"],
            pow_act_b=power_dict_b["power_active"],
            pow_act_c=power_dict_c["power_active"],
            pow_react_a=power_dict_a["power_reactive"],
            pow_react_b=power_dict_b["power_reactive"],
            pow_react_c=power_dict_c["power_reactive"],
            cosphi_a=power_dict_a["cosphi"],
            cosphi_b=power_dict_b["cosphi"],
            cosphi_c=power_dict_c["cosphi"],
            cosphi_dir=cosphi_dir,
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
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_ip(
            voltage=voltage,
            current=current_a,
            pow_act=pow_act_a,
            cosphi_dir=cosphi_dir,
            scaling=scaling,
        )
        power_dict_b = cls.calc_ip(
            voltage=voltage,
            current=current_b,
            pow_act=pow_act_b,
            cosphi_dir=cosphi_dir,
            scaling=scaling,
        )
        power_dict_c = cls.calc_ip(
            voltage=voltage,
            current=current_c,
            pow_act=pow_act_c,
            cosphi_dir=cosphi_dir,
            scaling=scaling,
        )
        return LoadPower(
            pow_app_a=power_dict_a["power_apparent"],
            pow_app_b=power_dict_b["power_apparent"],
            pow_app_c=power_dict_c["power_apparent"],
            pow_act_a=power_dict_a["power_active"],
            pow_act_b=power_dict_b["power_active"],
            pow_act_c=power_dict_c["power_active"],
            pow_react_a=power_dict_a["power_reactive"],
            pow_react_b=power_dict_b["power_reactive"],
            pow_react_c=power_dict_c["power_reactive"],
            cosphi_a=power_dict_a["cosphi"],
            cosphi_b=power_dict_b["cosphi"],
            cosphi_c=power_dict_c["cosphi"],
            cosphi_dir=cosphi_dir,
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
        cosphi_dir: CosphiDir,
        scaling: float,
    ) -> LoadPower:
        power_dict_a = cls.calc_sp(pow_app=pow_app_a, pow_act=pow_act_a, cosphi_dir=cosphi_dir, scaling=scaling)
        power_dict_b = cls.calc_sp(pow_app=pow_app_b, pow_act=pow_act_b, cosphi_dir=cosphi_dir, scaling=scaling)
        power_dict_c = cls.calc_sp(pow_app=pow_app_c, pow_act=pow_act_c, cosphi_dir=cosphi_dir, scaling=scaling)
        return LoadPower(
            pow_app_a=power_dict_a["power_apparent"],
            pow_app_b=power_dict_b["power_apparent"],
            pow_app_c=power_dict_c["power_apparent"],
            pow_act_a=power_dict_a["power_active"],
            pow_act_b=power_dict_b["power_active"],
            pow_act_c=power_dict_c["power_active"],
            pow_react_a=power_dict_a["power_reactive"],
            pow_react_b=power_dict_b["power_reactive"],
            pow_react_c=power_dict_c["power_reactive"],
            cosphi_a=power_dict_a["cosphi"],
            cosphi_b=power_dict_b["cosphi"],
            cosphi_c=power_dict_c["cosphi"],
            cosphi_dir=cosphi_dir,
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
        if not (power_dict_a["cosphi_dir"] == power_dict_b["cosphi_dir"] == power_dict_c["cosphi_dir"]):
            msg = "Cosphi directions do not match."
            raise ValueError(msg)

        cosphi_dir = power_dict_a["cosphi_dir"]
        return LoadPower(
            pow_app_a=power_dict_a["power_apparent"],
            pow_app_b=power_dict_b["power_apparent"],
            pow_app_c=power_dict_c["power_apparent"],
            pow_act_a=power_dict_a["power_active"],
            pow_act_b=power_dict_b["power_active"],
            pow_act_c=power_dict_c["power_active"],
            pow_react_a=power_dict_a["power_reactive"],
            pow_react_b=power_dict_b["power_reactive"],
            pow_react_c=power_dict_c["power_reactive"],
            cosphi_a=power_dict_a["cosphi"],
            cosphi_b=power_dict_b["cosphi"],
            cosphi_c=power_dict_c["cosphi"],
            cosphi_dir=cosphi_dir,
        )

    def as_active_power_ssc(self) -> ActivePower:
        return ActivePower(
            value=round(self.pow_act, DecimalDigits.POWER),
            value_a=round(self.pow_act_a, DecimalDigits.POWER + 2),
            value_b=round(self.pow_act_b, DecimalDigits.POWER + 2),
            value_c=round(self.pow_act_c, DecimalDigits.POWER + 2),
            is_symmetrical=self.is_symmetrical,
        )

    def as_reactive_power_ssc(self, controller: Controller | None = None) -> ReactivePower:
        # remark: actual reactive power set by external controller is not shown in ReactivePower
        return ReactivePower(
            value=round(self.pow_react, DecimalDigits.POWER),
            value_a=round(self.pow_react_a, DecimalDigits.POWER + 2),
            value_b=round(self.pow_react_b, DecimalDigits.POWER + 2),
            value_c=round(self.pow_react_c, DecimalDigits.POWER + 2),
            is_symmetrical=self.is_symmetrical,
            controller=controller,
        )

    def as_rated_power(self) -> RatedPower:
        return RatedPower(
            value=round(self.pow_app, DecimalDigits.POWER),
            cosphi=round(self.cosphi, DecimalDigits.COSPHI),
            value_a=round(self.pow_app_a, DecimalDigits.POWER + 2),
            value_b=round(self.pow_app_b, DecimalDigits.POWER + 2),
            value_c=round(self.pow_app_c, DecimalDigits.POWER + 2),
            cosphi_a=round(self.cosphi_a, DecimalDigits.COSPHI),
            cosphi_b=round(self.cosphi_b, DecimalDigits.COSPHI),
            cosphi_c=round(self.cosphi_c, DecimalDigits.COSPHI),
        )
