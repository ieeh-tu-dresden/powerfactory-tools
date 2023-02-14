# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_tools.constants import DecimalDigits
from powerfactory_tools.constants import Exponents
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


@dataclass
class LoadPower:
    pow_app_r: float
    pow_app_s: float
    pow_app_t: float
    pow_act_r: float
    pow_act_s: float
    pow_act_t: float
    pow_react_r: float
    pow_react_s: float
    pow_react_t: float
    cosphi_r: float
    cosphi_s: float
    cosphi_t: float

    @property
    def pow_app(self) -> float:
        return self.pow_app_r + self.pow_app_s + self.pow_app_t

    @property
    def pow_app_abs(self) -> float:
        return abs(self.pow_app_r) + abs(self.pow_app_s) + abs(self.pow_app_t)

    @property
    def pow_act(self) -> float:
        return self.pow_act_r + self.pow_act_s + self.pow_act_t

    @property
    def pow_react(self) -> float:
        return self.pow_react_r + self.pow_react_s + self.pow_react_t

    @property
    def cosphi(self) -> float:
        try:
            return self.pow_act / self.pow_app
        except ZeroDivisionError:
            return 0

    @property
    def is_symmetrical(self) -> bool:
        return self.is_symmetrical_s and self.is_symmetrical_p and self.is_symmetrical_q and self.is_symmetrical_cosphi

    @property
    def is_symmetrical_s(self) -> bool:
        return self.pow_app_r == self.pow_app_s == self.pow_app_t

    @property
    def is_symmetrical_p(self) -> bool:
        return self.pow_act_r == self.pow_act_s == self.pow_act_t

    @property
    def is_symmetrical_q(self) -> bool:
        return self.pow_react_r == self.pow_react_s == self.pow_react_t

    @property
    def is_symmetrical_cosphi(self) -> bool:
        return self.cosphi_r == self.cosphi_s == self.cosphi_t

    @property
    def is_empty(self) -> bool:
        return self.pow_app_r == 0

    @staticmethod
    def calc_pq(
        *,
        pow_act: float,
        pow_react: float,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        pow_react = pow_react * scaling * Exponents.POWER
        pow_app = math.sqrt(pow_act**2 + pow_react**2)
        try:
            cosphi = pow_act / pow_app
        except ZeroDivisionError:
            cosphi = 0

        return {"power_apparent": pow_app, "power_active": pow_act, "power_reactive": pow_react, "cosphi": cosphi}

    @staticmethod
    def calc_pc(
        *,
        pow_act: float,
        cosphi: float,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        try:
            pow_app = pow_act / cosphi
        except ZeroDivisionError:
            logger.warning("`cosphi` is 0, but only active power is given. Actual state could not be determined.")
            return {"power_apparent": 0, "power_active": 0, "power_reactive": 0, "cosphi": 0}

        pow_react = math.sqrt(pow_app**2 - pow_act**2)
        return {"power_apparent": pow_app, "power_active": pow_act, "power_reactive": pow_react, "cosphi": cosphi}

    @staticmethod
    def calc_ic(
        *,
        voltage: float,
        current: float,
        cosphi: float,
        scaling: float,
    ) -> PowerDict:
        pow_app = voltage * current * scaling * Exponents.POWER
        pow_act = pow_app * cosphi
        pow_react = math.sqrt(pow_app**2 - pow_act**2)
        return {"power_apparent": pow_app, "power_active": pow_act, "power_reactive": pow_react, "cosphi": cosphi}

    @staticmethod
    def calc_sc(
        *,
        pow_app: float,
        cosphi: float,
        scaling: float,
    ) -> PowerDict:
        pow_app = pow_app * scaling * Exponents.POWER
        pow_act = pow_app * cosphi
        pow_react = math.sqrt(pow_app**2 - pow_act**2)
        return {"power_apparent": pow_app, "power_active": pow_act, "power_reactive": pow_react, "cosphi": cosphi}

    @staticmethod
    def calc_qc(
        *,
        pow_react: float,
        cosphi: float,
        scaling: float,
    ) -> PowerDict:
        pow_react = pow_react * scaling * Exponents.POWER
        try:
            pow_app = pow_react / math.sin(math.acos(cosphi))
        except ZeroDivisionError:
            logger.warning("`cosphi` is 1, but only reactive power is given. Actual state could not be determined.")
            return {"power_apparent": 0, "power_active": 0, "power_reactive": 0, "cosphi": 0}

        pow_act = pow_app * cosphi
        return {"power_apparent": pow_app, "power_active": pow_act, "power_reactive": pow_react, "cosphi": cosphi}

    @staticmethod
    def calc_ip(
        *,
        voltage: float,
        current: float,
        pow_act: float,
        scaling: float,
    ) -> PowerDict:
        pow_act = pow_act * scaling * Exponents.POWER
        pow_app = voltage * current * scaling * Exponents.POWER
        try:
            cosphi = pow_act / pow_app
        except ZeroDivisionError:
            cosphi = 0

        pow_react = math.sqrt(pow_app**2 - pow_act**2)
        return {"power_apparent": pow_app, "power_active": pow_act, "power_reactive": pow_react, "cosphi": cosphi}

    @staticmethod
    def calc_sp(
        *,
        pow_app: float,
        pow_act: float,
        scaling: float,
    ) -> PowerDict:
        pow_app = pow_app * scaling * Exponents.POWER
        pow_act = pow_act * scaling * Exponents.POWER
        cosphi = pow_app / pow_act
        pow_react = math.sqrt(pow_app**2 - pow_act**2)
        return {"power_apparent": pow_app, "power_active": pow_act, "power_reactive": pow_react, "cosphi": cosphi}

    @staticmethod
    def calc_sq(
        *,
        pow_app: float,
        pow_react: float,
        scaling: float,
    ) -> PowerDict:
        pow_app = pow_app * scaling * Exponents.POWER
        pow_react = pow_react * scaling * Exponents.POWER
        pow_act = math.sqrt(pow_app**2 - pow_react**2)
        try:
            cosphi = pow_act / pow_app
        except ZeroDivisionError:
            cosphi = 0

        return {"power_apparent": pow_app, "power_active": pow_act, "power_reactive": pow_react, "cosphi": cosphi}

    @classmethod
    def from_pq_sym(
        cls,
        *,
        pow_act: float,
        pow_react: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_pq(pow_act=pow_act, pow_react=pow_react, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict["power_apparent"] / 3,
            pow_app_s=power_dict["power_apparent"] / 3,
            pow_app_t=power_dict["power_apparent"] / 3,
            pow_act_r=power_dict["power_active"] / 3,
            pow_act_s=power_dict["power_active"] / 3,
            pow_act_t=power_dict["power_active"] / 3,
            pow_react_r=power_dict["power_reactive"] / 3,
            pow_react_s=power_dict["power_reactive"] / 3,
            pow_react_t=power_dict["power_reactive"] / 3,
            cosphi_r=power_dict["cosphi"],
            cosphi_s=power_dict["cosphi"],
            cosphi_t=power_dict["cosphi"],
        )

    @classmethod
    def from_pc_sym(
        cls,
        *,
        pow_act: float,
        cosphi: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_pc(pow_act=pow_act, cosphi=cosphi, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict["power_apparent"] / 3,
            pow_app_s=power_dict["power_apparent"] / 3,
            pow_app_t=power_dict["power_apparent"] / 3,
            pow_act_r=power_dict["power_active"] / 3,
            pow_act_s=power_dict["power_active"] / 3,
            pow_act_t=power_dict["power_active"] / 3,
            pow_react_r=power_dict["power_reactive"] / 3,
            pow_react_s=power_dict["power_reactive"] / 3,
            pow_react_t=power_dict["power_reactive"] / 3,
            cosphi_r=power_dict["cosphi"],
            cosphi_s=power_dict["cosphi"],
            cosphi_t=power_dict["cosphi"],
        )

    @classmethod
    def from_ic_sym(
        cls,
        *,
        voltage: float,
        current: float,
        cosphi: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_ic(voltage=voltage, current=current, cosphi=cosphi, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict["power_apparent"] / 3,
            pow_app_s=power_dict["power_apparent"] / 3,
            pow_app_t=power_dict["power_apparent"] / 3,
            pow_act_r=power_dict["power_active"] / 3,
            pow_act_s=power_dict["power_active"] / 3,
            pow_act_t=power_dict["power_active"] / 3,
            pow_react_r=power_dict["power_reactive"] / 3,
            pow_react_s=power_dict["power_reactive"] / 3,
            pow_react_t=power_dict["power_reactive"] / 3,
            cosphi_r=power_dict["cosphi"],
            cosphi_s=power_dict["cosphi"],
            cosphi_t=power_dict["cosphi"],
        )

    @classmethod
    def from_sc_sym(
        cls,
        *,
        pow_app: float,
        cosphi: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_sc(pow_app=pow_app, cosphi=cosphi, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict["power_apparent"] / 3,
            pow_app_s=power_dict["power_apparent"] / 3,
            pow_app_t=power_dict["power_apparent"] / 3,
            pow_act_r=power_dict["power_active"] / 3,
            pow_act_s=power_dict["power_active"] / 3,
            pow_act_t=power_dict["power_active"] / 3,
            pow_react_r=power_dict["power_reactive"] / 3,
            pow_react_s=power_dict["power_reactive"] / 3,
            pow_react_t=power_dict["power_reactive"] / 3,
            cosphi_r=power_dict["cosphi"],
            cosphi_s=power_dict["cosphi"],
            cosphi_t=power_dict["cosphi"],
        )

    @classmethod
    def from_qc_sym(
        cls,
        *,
        pow_react: float,
        cosphi: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_qc(pow_react=pow_react, cosphi=cosphi, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict["power_apparent"] / 3,
            pow_app_s=power_dict["power_apparent"] / 3,
            pow_app_t=power_dict["power_apparent"] / 3,
            pow_act_r=power_dict["power_active"] / 3,
            pow_act_s=power_dict["power_active"] / 3,
            pow_act_t=power_dict["power_active"] / 3,
            pow_react_r=power_dict["power_reactive"] / 3,
            pow_react_s=power_dict["power_reactive"] / 3,
            pow_react_t=power_dict["power_reactive"] / 3,
            cosphi_r=power_dict["cosphi"],
            cosphi_s=power_dict["cosphi"],
            cosphi_t=power_dict["cosphi"],
        )

    @classmethod
    def from_ip_sym(
        cls,
        *,
        voltage: float,
        current: float,
        pow_act: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_ip(voltage=voltage, current=current, pow_act=pow_act, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict["power_apparent"] / 3,
            pow_app_s=power_dict["power_apparent"] / 3,
            pow_app_t=power_dict["power_apparent"] / 3,
            pow_act_r=power_dict["power_active"] / 3,
            pow_act_s=power_dict["power_active"] / 3,
            pow_act_t=power_dict["power_active"] / 3,
            pow_react_r=power_dict["power_reactive"] / 3,
            pow_react_s=power_dict["power_reactive"] / 3,
            pow_react_t=power_dict["power_reactive"] / 3,
            cosphi_r=power_dict["cosphi"],
            cosphi_s=power_dict["cosphi"],
            cosphi_t=power_dict["cosphi"],
        )

    @classmethod
    def from_sp_sym(
        cls,
        *,
        pow_app: float,
        pow_act: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_sp(pow_app=pow_app, pow_act=pow_act, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict["power_apparent"] / 3,
            pow_app_s=power_dict["power_apparent"] / 3,
            pow_app_t=power_dict["power_apparent"] / 3,
            pow_act_r=power_dict["power_active"] / 3,
            pow_act_s=power_dict["power_active"] / 3,
            pow_act_t=power_dict["power_active"] / 3,
            pow_react_r=power_dict["power_reactive"] / 3,
            pow_react_s=power_dict["power_reactive"] / 3,
            pow_react_t=power_dict["power_reactive"] / 3,
            cosphi_r=power_dict["cosphi"],
            cosphi_s=power_dict["cosphi"],
            cosphi_t=power_dict["cosphi"],
        )

    @classmethod
    def from_sq_sym(
        cls,
        *,
        pow_app: float,
        pow_react: float,
        scaling: float,
    ) -> LoadPower:
        power_dict = cls.calc_sq(pow_app=pow_app, pow_react=pow_react, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict["power_apparent"] / 3,
            pow_app_s=power_dict["power_apparent"] / 3,
            pow_app_t=power_dict["power_apparent"] / 3,
            pow_act_r=power_dict["power_active"] / 3,
            pow_act_s=power_dict["power_active"] / 3,
            pow_act_t=power_dict["power_active"] / 3,
            pow_react_r=power_dict["power_reactive"] / 3,
            pow_react_s=power_dict["power_reactive"] / 3,
            pow_react_t=power_dict["power_reactive"] / 3,
            cosphi_r=power_dict["cosphi"],
            cosphi_s=power_dict["cosphi"],
            cosphi_t=power_dict["cosphi"],
        )

    @classmethod
    def from_pq_asym(
        cls,
        *,
        pow_act_r: float,
        pow_act_s: float,
        pow_act_t: float,
        pow_react_r: float,
        pow_react_s: float,
        pow_react_t: float,
        scaling: float,
    ) -> LoadPower:
        power_dict_r = cls.calc_pq(pow_act=pow_act_r, pow_react=pow_react_r, scaling=scaling)
        power_dict_s = cls.calc_pq(pow_act=pow_act_s, pow_react=pow_react_s, scaling=scaling)
        power_dict_t = cls.calc_pq(pow_act=pow_act_t, pow_react=pow_react_t, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict_r["power_apparent"],
            pow_app_s=power_dict_s["power_apparent"],
            pow_app_t=power_dict_t["power_apparent"],
            pow_act_r=power_dict_r["power_active"],
            pow_act_s=power_dict_s["power_active"],
            pow_act_t=power_dict_t["power_active"],
            pow_react_r=power_dict_r["power_reactive"],
            pow_react_s=power_dict_s["power_reactive"],
            pow_react_t=power_dict_t["power_reactive"],
            cosphi_r=power_dict_r["cosphi"],
            cosphi_s=power_dict_s["cosphi"],
            cosphi_t=power_dict_t["cosphi"],
        )

    @classmethod
    def from_pc_asym(
        cls,
        *,
        pow_act_r: float,
        pow_act_s: float,
        pow_act_t: float,
        cosphi_r: float,
        cosphi_s: float,
        cosphi_t: float,
        scaling: float,
    ) -> LoadPower:
        power_dict_r = cls.calc_pc(pow_act=pow_act_r, cosphi=cosphi_r, scaling=scaling)
        power_dict_s = cls.calc_pc(pow_act=pow_act_s, cosphi=cosphi_s, scaling=scaling)
        power_dict_t = cls.calc_pc(pow_act=pow_act_t, cosphi=cosphi_t, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict_r["power_apparent"],
            pow_app_s=power_dict_s["power_apparent"],
            pow_app_t=power_dict_t["power_apparent"],
            pow_act_r=power_dict_r["power_active"],
            pow_act_s=power_dict_s["power_active"],
            pow_act_t=power_dict_t["power_active"],
            pow_react_r=power_dict_r["power_reactive"],
            pow_react_s=power_dict_s["power_reactive"],
            pow_react_t=power_dict_t["power_reactive"],
            cosphi_r=power_dict_r["cosphi"],
            cosphi_s=power_dict_s["cosphi"],
            cosphi_t=power_dict_t["cosphi"],
        )

    @classmethod
    def from_ic_asym(
        cls,
        *,
        voltage: float,
        current_r: float,
        current_s: float,
        current_t: float,
        cosphi_r: float,
        cosphi_s: float,
        cosphi_t: float,
        scaling: float,
    ) -> LoadPower:
        voltage = voltage / math.sqrt(3)  # for asymmetric calc, u_le has to be used instead of u_ll
        power_dict_r = cls.calc_ic(voltage=voltage, current=current_r, cosphi=cosphi_r, scaling=scaling)
        power_dict_s = cls.calc_ic(voltage=voltage, current=current_s, cosphi=cosphi_s, scaling=scaling)
        power_dict_t = cls.calc_ic(voltage=voltage, current=current_t, cosphi=cosphi_t, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict_r["power_apparent"],
            pow_app_s=power_dict_s["power_apparent"],
            pow_app_t=power_dict_t["power_apparent"],
            pow_act_r=power_dict_r["power_active"],
            pow_act_s=power_dict_s["power_active"],
            pow_act_t=power_dict_t["power_active"],
            pow_react_r=power_dict_r["power_reactive"],
            pow_react_s=power_dict_s["power_reactive"],
            pow_react_t=power_dict_t["power_reactive"],
            cosphi_r=power_dict_r["cosphi"],
            cosphi_s=power_dict_s["cosphi"],
            cosphi_t=power_dict_t["cosphi"],
        )

    @classmethod
    def from_sc_asym(
        cls,
        *,
        pow_app_r: float,
        pow_app_s: float,
        pow_app_t: float,
        cosphi_r: float,
        cosphi_s: float,
        cosphi_t: float,
        scaling: float,
    ) -> LoadPower:
        power_dict_r = cls.calc_sc(pow_app=pow_app_r, cosphi=cosphi_r, scaling=scaling)
        power_dict_s = cls.calc_sc(pow_app=pow_app_s, cosphi=cosphi_s, scaling=scaling)
        power_dict_t = cls.calc_sc(pow_app=pow_app_t, cosphi=cosphi_t, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict_r["power_apparent"],
            pow_app_s=power_dict_s["power_apparent"],
            pow_app_t=power_dict_t["power_apparent"],
            pow_act_r=power_dict_r["power_active"],
            pow_act_s=power_dict_s["power_active"],
            pow_act_t=power_dict_t["power_active"],
            pow_react_r=power_dict_r["power_reactive"],
            pow_react_s=power_dict_s["power_reactive"],
            pow_react_t=power_dict_t["power_reactive"],
            cosphi_r=power_dict_r["cosphi"],
            cosphi_s=power_dict_s["cosphi"],
            cosphi_t=power_dict_t["cosphi"],
        )

    @classmethod
    def from_qc_asym(
        cls,
        *,
        pow_react_r: float,
        pow_react_s: float,
        pow_react_t: float,
        cosphi_r: float,
        cosphi_s: float,
        cosphi_t: float,
        scaling: float,
    ) -> LoadPower:
        power_dict_r = cls.calc_qc(pow_react=pow_react_r, cosphi=cosphi_r, scaling=scaling)
        power_dict_s = cls.calc_qc(pow_react=pow_react_s, cosphi=cosphi_s, scaling=scaling)
        power_dict_t = cls.calc_qc(pow_react=pow_react_t, cosphi=cosphi_t, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict_r["power_apparent"],
            pow_app_s=power_dict_s["power_apparent"],
            pow_app_t=power_dict_t["power_apparent"],
            pow_act_r=power_dict_r["power_active"],
            pow_act_s=power_dict_s["power_active"],
            pow_act_t=power_dict_t["power_active"],
            pow_react_r=power_dict_r["power_reactive"],
            pow_react_s=power_dict_s["power_reactive"],
            pow_react_t=power_dict_t["power_reactive"],
            cosphi_r=power_dict_r["cosphi"],
            cosphi_s=power_dict_s["cosphi"],
            cosphi_t=power_dict_t["cosphi"],
        )

    @classmethod
    def from_ip_asym(
        cls,
        *,
        voltage: float,
        current_r: float,
        current_s: float,
        current_t: float,
        pow_act_r: float,
        pow_act_s: float,
        pow_act_t: float,
        scaling: float,
    ) -> LoadPower:
        voltage = voltage / math.sqrt(3)  # for asymmetric calc, u_le has to be used instead of u_ll
        power_dict_r = cls.calc_ip(voltage=voltage, current=current_r, pow_act=pow_act_r, scaling=scaling)
        power_dict_s = cls.calc_ip(voltage=voltage, current=current_s, pow_act=pow_act_s, scaling=scaling)
        power_dict_t = cls.calc_ip(voltage=voltage, current=current_t, pow_act=pow_act_t, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict_r["power_apparent"],
            pow_app_s=power_dict_s["power_apparent"],
            pow_app_t=power_dict_t["power_apparent"],
            pow_act_r=power_dict_r["power_active"],
            pow_act_s=power_dict_s["power_active"],
            pow_act_t=power_dict_t["power_active"],
            pow_react_r=power_dict_r["power_reactive"],
            pow_react_s=power_dict_s["power_reactive"],
            pow_react_t=power_dict_t["power_reactive"],
            cosphi_r=power_dict_r["cosphi"],
            cosphi_s=power_dict_s["cosphi"],
            cosphi_t=power_dict_t["cosphi"],
        )

    @classmethod
    def from_sp_asym(
        cls,
        *,
        pow_app_r: float,
        pow_app_s: float,
        pow_app_t: float,
        pow_act_r: float,
        pow_act_s: float,
        pow_act_t: float,
        scaling: float,
    ) -> LoadPower:
        power_dict_r = cls.calc_sp(pow_app=pow_app_r, pow_act=pow_act_r, scaling=scaling)
        power_dict_s = cls.calc_sp(pow_app=pow_app_s, pow_act=pow_act_s, scaling=scaling)
        power_dict_t = cls.calc_sp(pow_app=pow_app_t, pow_act=pow_act_t, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict_r["power_apparent"],
            pow_app_s=power_dict_s["power_apparent"],
            pow_app_t=power_dict_t["power_apparent"],
            pow_act_r=power_dict_r["power_active"],
            pow_act_s=power_dict_s["power_active"],
            pow_act_t=power_dict_t["power_active"],
            pow_react_r=power_dict_r["power_reactive"],
            pow_react_s=power_dict_s["power_reactive"],
            pow_react_t=power_dict_t["power_reactive"],
            cosphi_r=power_dict_r["cosphi"],
            cosphi_s=power_dict_s["cosphi"],
            cosphi_t=power_dict_t["cosphi"],
        )

    @classmethod
    def from_sq_asym(
        cls,
        *,
        pow_app_r: float,
        pow_app_s: float,
        pow_app_t: float,
        pow_react_r: float,
        pow_react_s: float,
        pow_react_t: float,
        scaling: float,
    ) -> LoadPower:
        power_dict_r = cls.calc_sq(pow_app=pow_app_r, pow_react=pow_react_r, scaling=scaling)
        power_dict_s = cls.calc_sq(pow_app=pow_app_s, pow_react=pow_react_s, scaling=scaling)
        power_dict_t = cls.calc_sq(pow_app=pow_app_t, pow_react=pow_react_t, scaling=scaling)
        return LoadPower(
            pow_app_r=power_dict_r["power_apparent"],
            pow_app_s=power_dict_s["power_apparent"],
            pow_app_t=power_dict_t["power_apparent"],
            pow_act_r=power_dict_r["power_active"],
            pow_act_s=power_dict_s["power_active"],
            pow_act_t=power_dict_t["power_active"],
            pow_react_r=power_dict_r["power_reactive"],
            pow_react_s=power_dict_s["power_reactive"],
            pow_react_t=power_dict_t["power_reactive"],
            cosphi_r=power_dict_r["cosphi"],
            cosphi_s=power_dict_s["cosphi"],
            cosphi_t=power_dict_t["cosphi"],
        )

    def as_active_power_ssc(self) -> ActivePower:
        return ActivePower(
            value_0=round(self.pow_act, DecimalDigits.POWER),
            value_r_0=round(self.pow_act_r, DecimalDigits.POWER + 2),
            value_s_0=round(self.pow_act_s, DecimalDigits.POWER + 2),
            value_t_0=round(self.pow_act_t, DecimalDigits.POWER + 2),
            is_symmetrical=self.is_symmetrical,
        )

    def as_reactive_power_ssc(self, controller: Controller | None = None) -> ReactivePower:
        return ReactivePower(
            value_0=round(self.pow_react, DecimalDigits.POWER),
            value_r_0=round(self.pow_react_r, DecimalDigits.POWER + 2),
            value_s_0=round(self.pow_react_s, DecimalDigits.POWER + 2),
            value_t_0=round(self.pow_react_t, DecimalDigits.POWER + 2),
            is_symmetrical=self.is_symmetrical,
            controller=controller,
        )

    def as_rated_power(self) -> RatedPower:
        return RatedPower(
            value=round(self.pow_app, DecimalDigits.POWER),
            cosphi=round(self.cosphi, DecimalDigits.COSPHI),
            value_r=round(self.pow_app_r, DecimalDigits.POWER + 2),
            value_s=round(self.pow_app_s, DecimalDigits.POWER + 2),
            value_t=round(self.pow_app_t, DecimalDigits.POWER + 2),
            cosphi_r=round(self.cosphi_r, DecimalDigits.COSPHI),
            cosphi_s=round(self.cosphi_s, DecimalDigits.COSPHI),
            cosphi_t=round(self.cosphi_t, DecimalDigits.COSPHI),
        )
