# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import root_validator
from pydantic import validator

from powerfactory_utils.constants import DecimalDigits
from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.steadystate_case.controller import Controller

if TYPE_CHECKING:
    from typing import Any


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
    def validate_power(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: U100
        q_total = round(values["value_r_0"] + values["value_s_0"] + values["value_t_0"], DecimalDigits.POWER)
        if not (q_total == values["value_0"]):
            raise ValueError(f"Power mismatch: Total reactive values should be {q_total}, is {values['value_0']}.")

        return values
