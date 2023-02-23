# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pydantic

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.steadystate_case.controller import Controller  # noqa: TCH001

if TYPE_CHECKING:
    from typing import Any

THRESHOLD = 0.51  # acceptable rounding error (0.5 W) + epsilon for calculation accuracy (0.01 W)


class ReactivePower(Base):
    value_0: float  # actual reactive power (three-phase)
    value_a_0: float  # actual reactive power (phase a)
    value_b_0: float  # actual reactive power (phase b)
    value_c_0: float  # actual reactive power (phase c)
    is_symmetrical: bool
    controller: Controller | None = None

    @pydantic.root_validator
    def validate_power(cls, values: dict[str, Any]) -> dict[str, Any]:
        q_total = values["value_a_0"] + values["value_b_0"] + values["value_c_0"]
        diff = abs(values["value_0"] - q_total)
        if diff > THRESHOLD:
            msg = f"Power mismatch: Total reactive power should be {q_total}, is {values['value_0']}."
            raise ValueError(msg)

        return values

    @pydantic.root_validator
    def validate_symmetry(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values["is_symmetrical"] and not (values["value_a_0"] == values["value_b_0"] == values["value_c_0"]):
            msg = "Power mismatch: Three-phase reactive power of load is not symmetrical."
            raise ValueError(msg)

        return values
