from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from pydantic import root_validator
from pydantic import validator

from powerfactory_utils.constants import DecimalDigits
from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.steadystate_case.controller import Controller

if TYPE_CHECKING:
    from typing import Any


class ReactivePower(Base):
    q_0: float  # actual reactive power (three-phase)
    q_r_0: float  # actual reactive power (phase r)
    q_s_0: float  # actual reactive power (phase s)
    q_t_0: float  # actual reactive power (phase t)
    symmetrical: bool
    controller: Optional[Controller] = None

    class Config:
        frozen = True

    @validator("controller")
    def validate_controller(cls, v: Controller) -> Controller:
        return v

    @root_validator
    def validate_power(cls, values: dict[str, Any]) -> dict[str, Any]:
        q_total = round(values["q_r_0"] + values["q_s_0"] + values["q_t_0"], DecimalDigits.POWER)
        if not (q_total == values["q_0"]):
            raise ValueError(f"Power mismatch: Total reactive power should be {q_total}, is {values['q_0']}.")
        return values
