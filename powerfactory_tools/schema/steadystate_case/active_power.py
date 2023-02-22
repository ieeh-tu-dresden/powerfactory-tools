# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pydantic

from powerfactory_tools.constants import DecimalDigits
from powerfactory_tools.schema.base import Base

if TYPE_CHECKING:
    from typing import Any


class ActivePower(Base):
    value_0: float  # actual active power (three-phase)
    value_a_0: float  # actual active power (phase a)
    value_b_0: float  # actual active power (phase b)
    value_c_0: float  # actual active power (phase c)
    is_symmetrical: bool

    @pydantic.root_validator
    def validate_power(cls, values: dict[str, Any]) -> dict[str, Any]:
        p_total = round(values["value_a_0"] + values["value_b_0"] + values["value_c_0"], DecimalDigits.POWER)
        if p_total != values["value_0"]:
            msg = f"Power mismatch: Total active power should be {p_total}, is {values['value_0']}."
            raise ValueError(msg)

        return values

    @pydantic.root_validator
    def validate_symmetry(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["is_symmetrical"] and not (values["value_a_0"] == values["value_b_0"] == values["value_c_0"]):
            msg = "Power mismatch: Active power is not symmetrical."
            raise ValueError(msg)

        return values
