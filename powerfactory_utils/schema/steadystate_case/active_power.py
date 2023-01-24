# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import root_validator

from powerfactory_utils.constants import DecimalDigits
from powerfactory_utils.schema.base import Base

if TYPE_CHECKING:
    from typing import Any


class ActivePower(Base):
    value_0: float  # actual active power (three-phase)
    value_r_0: float  # actual active power (phase r)
    value_s_0: float  # actual active power (phase s)
    value_t_0: float  # actual active power (phase t)
    is_symmetrical: bool

    class Config:
        frozen = True

    @root_validator
    def validate_power(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: U100
        p_total = round(values["value_r_0"] + values["value_s_0"] + values["value_t_0"], DecimalDigits.POWER)
        if not (p_total == values["value_0"]):
            raise ValueError(f"Power mismatch: Total reactive power should be {p_total}, is {values['value_0']}.")

        return values
