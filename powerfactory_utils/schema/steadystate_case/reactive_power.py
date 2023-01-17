# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from pydantic import root_validator
from pydantic import validator

from powerfactory_utils.constants import DecimalDigits
from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.steadystate_case.controller import Controller


class ReactivePower(Base):
    value_0: float  # actual reactive power (three-phase)
    value_r_0: float  # actual reactive power (phase r)
    value_s_0: float  # actual reactive power (phase s)
    value_t_0: float  # actual reactive power (phase t)
    is_symmetrical: bool
    controller: Controller | None = None

    class Config:
        frozen = True

    @validator("controller")
    def validate_controller(cls, value: Controller) -> Controller:  # noqa: U100
        return value

    @root_validator
    def validate_power(cls, power: ReactivePower) -> ReactivePower:  # noqa: U100
        q_total = round(power.value_r_0 + power.value_s_0 + power.value_t_0, DecimalDigits.POWER)
        if not (q_total == power.value_0):
            raise ValueError(f"Power mismatch: Total reactive power should be {q_total}, is {power.value_0}.")

        return power
