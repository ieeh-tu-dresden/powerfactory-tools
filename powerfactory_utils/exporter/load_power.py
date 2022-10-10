from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from powerfactory_utils.constants import DecimalDigits
from powerfactory_utils.constants import Exponents
from powerfactory_utils.schema.steadystate_case.active_power import ActivePower
from powerfactory_utils.schema.steadystate_case.reactive_power import ReactivePower
from powerfactory_utils.schema.topology.load import RatedPower

if TYPE_CHECKING:
    from typing import Optional

    from powerfactory_utils.schema.steadystate_case.controller import Controller


@dataclass
class LoadPower:
    s_r: float
    s_s: float
    s_t: float
    p_r: float
    p_s: float
    p_t: float
    q_r: float
    q_s: float
    q_t: float
    cosphi_r: float
    cosphi_s: float
    cosphi_t: float

    @property
    def s(self) -> float:
        return self.s_r + self.s_s + self.s_t

    @property
    def s_abs(self) -> float:
        return abs(self.s_r) + abs(self.s_s) + abs(self.s_t)

    @property
    def p(self) -> float:
        return self.p_r + self.p_s + self.p_t

    @property
    def q(self) -> float:
        return self.q_r + self.q_s + self.q_t

    @property
    def cosphi(self) -> float:
        try:
            return self.p / self.s
        except ZeroDivisionError:
            return 0

    @property
    def symmetrical(self) -> bool:
        return self.symmetrical_s and self.symmetrical_p and self.symmetrical_q and self.symmetrical_cosphi

    @property
    def symmetrical_s(self) -> bool:
        return self.s_r == self.s_s == self.s_t

    @property
    def symmetrical_p(self) -> bool:
        return self.p_r == self.p_s == self.p_t

    @property
    def symmetrical_q(self) -> bool:
        return self.q_r == self.q_s == self.q_t

    @property
    def symmetrical_cosphi(self) -> bool:
        return self.cosphi_r == self.cosphi_s == self.cosphi_t

    @property
    def isempty(self) -> bool:
        return self.s_r == 0

    @staticmethod
    def calc_pq(p: float, q: float, scaling: float) -> tuple[float, float, float, float]:
        p = p * scaling * Exponents.POWER
        q = q * scaling * Exponents.POWER
        s = math.sqrt(p**2 + q**2)
        try:
            cosphi = p / s
        except ZeroDivisionError:
            cosphi = 0
        return s, p, q, cosphi

    @staticmethod
    def calc_pc(p: float, cosphi: float, scaling: float) -> tuple[float, float, float, float]:
        p = p * scaling * Exponents.POWER
        cosphi = cosphi
        try:
            s = p / cosphi
        except ZeroDivisionError:
            logger.warning("`cosphi` is 0, but only active power is given. Actual state could not be determined.")
            return 0, 0, 0, 0
        q = math.sqrt(s**2 - p**2)
        return s, p, q, cosphi

    @staticmethod
    def calc_ic(u: float, i: float, cosphi: float, scaling: float) -> tuple[float, float, float, float]:
        s = u * i * scaling * Exponents.POWER
        p = s * cosphi
        q = math.sqrt(s**2 - p**2)
        return s, p, q, cosphi

    @staticmethod
    def calc_sc(s: float, cosphi: float, scaling: float) -> tuple[float, float, float, float]:
        s = s * scaling * Exponents.POWER
        p = s * cosphi
        q = math.sqrt(s**2 - p**2)
        return s, p, q, cosphi

    @staticmethod
    def calc_qc(q: float, cosphi: float, scaling: float) -> tuple[float, float, float, float]:
        q = q * scaling * Exponents.POWER
        try:
            s = q / math.sin(math.acos(cosphi))
        except ZeroDivisionError:
            logger.warning("`cosphi` is 1, but only reactive power is given. Actual state could not be determined.")
            return 0, 0, 0, 0
        p = s * cosphi
        return s, p, q, cosphi

    @staticmethod
    def calc_ip(u: float, i: float, p: float, scaling: float) -> tuple[float, float, float, float]:
        p = p * scaling * Exponents.POWER
        s = u * i * scaling * Exponents.POWER
        try:
            cosphi = p / s
        except ZeroDivisionError:
            cosphi = 0
        q = math.sqrt(s**2 - p**2)
        return s, p, q, cosphi

    @staticmethod
    def calc_sp(s: float, p: float, scaling: float) -> tuple[float, float, float, float]:
        s = s * scaling * Exponents.POWER
        p = p * scaling * Exponents.POWER
        cosphi = s / p
        q = math.sqrt(s**2 - p**2)
        return s, p, q, cosphi

    @staticmethod
    def calc_sq(s: float, q: float, scaling: float) -> tuple[float, float, float, float]:
        s = s * scaling * Exponents.POWER
        q = q * scaling * Exponents.POWER
        p = math.sqrt(s**2 - q**2)
        try:
            cosphi = p / s
        except ZeroDivisionError:
            cosphi = 0
        return s, p, q, cosphi

    @classmethod
    def from_pq_sym(cls, p: float, q: float, scaling: float) -> LoadPower:
        s, p, q, cosphi = cls.calc_pq(p, q, scaling)
        return LoadPower(
            s_r=s / 3,
            s_s=s / 3,
            s_t=s / 3,
            p_r=p / 3,
            p_s=p / 3,
            p_t=p / 3,
            q_r=q / 3,
            q_s=q / 3,
            q_t=q / 3,
            cosphi_r=cosphi,
            cosphi_s=cosphi,
            cosphi_t=cosphi,
        )

    @classmethod
    def from_pc_sym(cls, p: float, cosphi: float, scaling: float) -> LoadPower:
        s, p, q, cosphi = cls.calc_pc(p, cosphi, scaling)
        return LoadPower(
            s_r=s / 3,
            s_s=s / 3,
            s_t=s / 3,
            p_r=p / 3,
            p_s=p / 3,
            p_t=p / 3,
            q_r=q / 3,
            q_s=q / 3,
            q_t=q / 3,
            cosphi_r=cosphi,
            cosphi_s=cosphi,
            cosphi_t=cosphi,
        )

    @classmethod
    def from_ic_sym(cls, u: float, i: float, cosphi: float, scaling: float) -> LoadPower:
        s, p, q, cosphi = cls.calc_ic(u, i, cosphi, scaling)
        return LoadPower(
            s_r=s / 3,
            s_s=s / 3,
            s_t=s / 3,
            p_r=p / 3,
            p_s=p / 3,
            p_t=p / 3,
            q_r=q / 3,
            q_s=q / 3,
            q_t=q / 3,
            cosphi_r=cosphi,
            cosphi_s=cosphi,
            cosphi_t=cosphi,
        )

    @classmethod
    def from_sc_sym(cls, s: float, cosphi: float, scaling: float) -> LoadPower:
        s, p, q, cosphi = cls.calc_sc(s, cosphi, scaling)
        return LoadPower(
            s_r=s / 3,
            s_s=s / 3,
            s_t=s / 3,
            p_r=p / 3,
            p_s=p / 3,
            p_t=p / 3,
            q_r=q / 3,
            q_s=q / 3,
            q_t=q / 3,
            cosphi_r=cosphi,
            cosphi_s=cosphi,
            cosphi_t=cosphi,
        )

    @classmethod
    def from_qc_sym(cls, q: float, cosphi: float, scaling: float) -> LoadPower:
        s, p, q, cosphi = cls.calc_qc(q, cosphi, scaling)
        return LoadPower(
            s_r=s / 3,
            s_s=s / 3,
            s_t=s / 3,
            p_r=p / 3,
            p_s=p / 3,
            p_t=p / 3,
            q_r=q / 3,
            q_s=q / 3,
            q_t=q / 3,
            cosphi_r=cosphi,
            cosphi_s=cosphi,
            cosphi_t=cosphi,
        )

    @classmethod
    def from_ip_sym(cls, u: float, i: float, p: float, scaling: float) -> LoadPower:
        s, p, q, cosphi = cls.calc_ip(u, i, p, scaling)
        return LoadPower(
            s_r=s / 3,
            s_s=s / 3,
            s_t=s / 3,
            p_r=p / 3,
            p_s=p / 3,
            p_t=p / 3,
            q_r=q / 3,
            q_s=q / 3,
            q_t=q / 3,
            cosphi_r=cosphi,
            cosphi_s=cosphi,
            cosphi_t=cosphi,
        )

    @classmethod
    def from_sp_sym(cls, s: float, p: float, scaling: float) -> LoadPower:
        s, p, q, cosphi = cls.calc_sp(s, p, scaling)
        return LoadPower(
            s_r=s / 3,
            s_s=s / 3,
            s_t=s / 3,
            p_r=p / 3,
            p_s=p / 3,
            p_t=p / 3,
            q_r=q / 3,
            q_s=q / 3,
            q_t=q / 3,
            cosphi_r=cosphi,
            cosphi_s=cosphi,
            cosphi_t=cosphi,
        )

    @classmethod
    def from_sq_sym(cls, s: float, q: float, scaling: float) -> LoadPower:
        s, p, q, cosphi = cls.calc_sq(s, q, scaling)
        return LoadPower(
            s_r=s / 3,
            s_s=s / 3,
            s_t=s / 3,
            p_r=p / 3,
            p_s=p / 3,
            p_t=p / 3,
            q_r=q / 3,
            q_s=q / 3,
            q_t=q / 3,
            cosphi_r=cosphi,
            cosphi_s=cosphi,
            cosphi_t=cosphi,
        )

    @classmethod
    def from_pq_asym(
        cls,
        p_r: float,
        p_s: float,
        p_t: float,
        q_r: float,
        q_s: float,
        q_t: float,
        scaling: float,
    ) -> LoadPower:
        s_r, p_r, q_r, cosphi_r = cls.calc_pq(p_r, q_r, scaling)
        s_s, p_s, q_s, cosphi_s = cls.calc_pq(p_s, q_s, scaling)
        s_t, p_t, q_t, cosphi_t = cls.calc_pq(p_t, q_t, scaling)
        return LoadPower(
            s_r=s_r,
            s_s=s_s,
            s_t=s_t,
            p_r=p_r,
            p_s=p_s,
            p_t=p_t,
            q_r=q_r,
            q_s=q_s,
            q_t=q_t,
            cosphi_r=cosphi_r,
            cosphi_s=cosphi_s,
            cosphi_t=cosphi_t,
        )

    @classmethod
    def from_pc_asym(
        cls,
        p_r: float,
        p_s: float,
        p_t: float,
        cosphi_r: float,
        cosphi_s: float,
        cosphi_t: float,
        scaling: float,
    ) -> LoadPower:
        s_r, p_r, q_r, cosphi_r = cls.calc_pc(p_r, cosphi_r, scaling)
        s_s, p_s, q_s, cosphi_s = cls.calc_pc(p_s, cosphi_s, scaling)
        s_t, p_t, q_t, cosphi_t = cls.calc_pc(p_t, cosphi_t, scaling)
        return LoadPower(
            s_r=s_r,
            s_s=s_s,
            s_t=s_t,
            p_r=p_r,
            p_s=p_s,
            p_t=p_t,
            q_r=q_r,
            q_s=q_s,
            q_t=q_t,
            cosphi_r=cosphi_r,
            cosphi_s=cosphi_s,
            cosphi_t=cosphi_t,
        )

    @classmethod
    def from_ic_asym(
        cls,
        u: float,
        i_r: float,
        i_s: float,
        i_t: float,
        cosphi_r: float,
        cosphi_s: float,
        cosphi_t: float,
        scaling: float,
    ) -> LoadPower:
        u = u / math.sqrt(3)  # for asymmetric calc, u_le has to be used instead of u_ll
        s_r, p_r, q_r, cosphi_r = cls.calc_ic(u, i_r, cosphi_r, scaling)
        s_s, p_s, q_s, cosphi_s = cls.calc_ic(u, i_s, cosphi_s, scaling)
        s_t, p_t, q_t, cosphi_t = cls.calc_ic(u, i_t, cosphi_t, scaling)
        return LoadPower(
            s_r=s_r,
            s_s=s_s,
            s_t=s_t,
            p_r=p_r,
            p_s=p_s,
            p_t=p_t,
            q_r=q_r,
            q_s=q_s,
            q_t=q_t,
            cosphi_r=cosphi_r,
            cosphi_s=cosphi_s,
            cosphi_t=cosphi_t,
        )

    @classmethod
    def from_sc_asym(
        cls,
        s_r: float,
        s_s: float,
        s_t: float,
        cosphi_r: float,
        cosphi_s: float,
        cosphi_t: float,
        scaling: float,
    ) -> LoadPower:
        s_r, p_r, q_r, cosphi_r = cls.calc_sc(s_r, cosphi_r, scaling)
        s_s, p_s, q_s, cosphi_s = cls.calc_sc(s_s, cosphi_s, scaling)
        s_t, p_t, q_t, cosphi_t = cls.calc_sc(s_t, cosphi_t, scaling)
        return LoadPower(
            s_r=s_r,
            s_s=s_s,
            s_t=s_t,
            p_r=p_r,
            p_s=p_s,
            p_t=p_t,
            q_r=q_r,
            q_s=q_s,
            q_t=q_t,
            cosphi_r=cosphi_r,
            cosphi_s=cosphi_s,
            cosphi_t=cosphi_t,
        )

    @classmethod
    def from_qc_asym(
        cls,
        q_r: float,
        q_s: float,
        q_t: float,
        cosphi_r: float,
        cosphi_s: float,
        cosphi_t: float,
        scaling: float,
    ) -> LoadPower:
        s_r, p_r, q_r, cosphi_r = cls.calc_qc(q_r, cosphi_r, scaling)
        s_s, p_s, q_s, cosphi_s = cls.calc_qc(q_s, cosphi_s, scaling)
        s_t, p_t, q_t, cosphi_t = cls.calc_qc(q_t, cosphi_t, scaling)
        return LoadPower(
            s_r=s_r,
            s_s=s_s,
            s_t=s_t,
            p_r=p_r,
            p_s=p_s,
            p_t=p_t,
            q_r=q_r,
            q_s=q_s,
            q_t=q_t,
            cosphi_r=cosphi_r,
            cosphi_s=cosphi_s,
            cosphi_t=cosphi_t,
        )

    @classmethod
    def from_ip_asym(
        cls,
        u: float,
        i_r: float,
        i_s: float,
        i_t: float,
        p_r: float,
        p_s: float,
        p_t: float,
        scaling: float,
    ) -> LoadPower:
        u = u / math.sqrt(3)  # for asymmetric calc, u_le has to be used instead of u_ll
        s_r, p_r, q_r, cosphi_r = cls.calc_ip(u, i_r, p_r, scaling)
        s_s, p_s, q_s, cosphi_s = cls.calc_ip(u, i_s, p_s, scaling)
        s_t, p_t, q_t, cosphi_t = cls.calc_ip(u, i_t, p_t, scaling)
        return LoadPower(
            s_r=s_r,
            s_s=s_s,
            s_t=s_t,
            p_r=p_r,
            p_s=p_s,
            p_t=p_t,
            q_r=q_r,
            q_s=q_s,
            q_t=q_t,
            cosphi_r=cosphi_r,
            cosphi_s=cosphi_s,
            cosphi_t=cosphi_t,
        )

    @classmethod
    def from_sp_asym(
        cls,
        s_r: float,
        s_s: float,
        s_t: float,
        p_r: float,
        p_s: float,
        p_t: float,
        scaling: float,
    ) -> LoadPower:
        s_r, p_r, q_r, cosphi_r = cls.calc_sp(s_r, p_r, scaling)
        s_s, p_s, q_s, cosphi_s = cls.calc_sp(s_s, p_s, scaling)
        s_t, p_t, q_t, cosphi_t = cls.calc_sp(s_t, p_t, scaling)
        return LoadPower(
            s_r=s_r,
            s_s=s_s,
            s_t=s_t,
            p_r=p_r,
            p_s=p_s,
            p_t=p_t,
            q_r=q_r,
            q_s=q_s,
            q_t=q_t,
            cosphi_r=cosphi_r,
            cosphi_s=cosphi_s,
            cosphi_t=cosphi_t,
        )

    @classmethod
    def from_sq_asym(
        cls,
        s_r: float,
        s_s: float,
        s_t: float,
        q_r: float,
        q_s: float,
        q_t: float,
        scaling: float,
    ) -> LoadPower:
        s_r, p_r, q_r, cosphi_r = cls.calc_sq(s_r, q_r, scaling)
        s_s, p_s, q_s, cosphi_s = cls.calc_sq(s_s, q_s, scaling)
        s_t, p_t, q_t, cosphi_t = cls.calc_sq(s_t, q_t, scaling)
        return LoadPower(
            s_r=s_r,
            s_s=s_s,
            s_t=s_t,
            p_r=p_r,
            p_s=p_s,
            p_t=p_t,
            q_r=q_r,
            q_s=q_s,
            q_t=q_t,
            cosphi_r=cosphi_r,
            cosphi_s=cosphi_s,
            cosphi_t=cosphi_t,
        )

    def as_active_power_ssc(self) -> ActivePower:
        return ActivePower(
            p_0=round(self.p, DecimalDigits.POWER),
            p_r_0=round(self.p_r, DecimalDigits.POWER + 2),
            p_s_0=round(self.p_s, DecimalDigits.POWER + 2),
            p_t_0=round(self.p_t, DecimalDigits.POWER + 2),
            symmetrical=self.symmetrical,
        )

    def as_reactive_power_ssc(self, controller: Optional[Controller] = None) -> ReactivePower:
        return ReactivePower(
            q_0=round(self.q, DecimalDigits.POWER),
            q_r_0=round(self.q_r, DecimalDigits.POWER + 2),
            q_s_0=round(self.q_s, DecimalDigits.POWER + 2),
            q_t_0=round(self.q_t, DecimalDigits.POWER + 2),
            symmetrical=self.symmetrical,
            controller=controller,
        )

    def as_rated_power(self) -> RatedPower:
        return RatedPower(
            s=round(self.s, DecimalDigits.POWER),
            cosphi=round(self.cosphi, DecimalDigits.COSPHI),
            s_r=round(self.s_r, DecimalDigits.POWER + 2),
            s_s=round(self.s_s, DecimalDigits.POWER + 2),
            s_t=round(self.s_t, DecimalDigits.POWER + 2),
            cosphi_r=round(self.cosphi_r, DecimalDigits.COSPHI),
            cosphi_s=round(self.cosphi_s, DecimalDigits.COSPHI),
            cosphi_t=round(self.cosphi_t, DecimalDigits.COSPHI),
        )
