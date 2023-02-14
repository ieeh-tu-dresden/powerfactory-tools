#! /usr/bin/python
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pydantic

from powerfactory_tools.constants import DecimalDigits
from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.steadystate_case.controller import Controller  # noqa: TCH001

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

    @pydantic.validator("controller")
    def validate_controller(cls, value: Controller) -> Controller:
        return value

    @pydantic.root_validator
    def validate_power(cls, values: dict[str, Any]) -> dict[str, Any]:
        q_total = round(values["value_r_0"] + values["value_s_0"] + values["value_t_0"], DecimalDigits.POWER)
        if q_total != values["value_0"]:
            msg = f"Power mismatch: Total reactive values should be {q_total}, is {values['value_0']}."
            raise ValueError(msg)

        return values
