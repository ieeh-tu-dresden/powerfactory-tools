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
    def validate_power(cls, values: dict[str, Any]) -> dict[str, Any]:
        p_total = round(values["p_r_0"] + values["p_s_0"] + values["p_t_0"], DecimalDigits.POWER)
        if not (p_total == values["p_0"]):
            raise ValueError(f"Power mismatch: Total reactive power should be {p_total}, is {values['p_0']}.")
        return values
