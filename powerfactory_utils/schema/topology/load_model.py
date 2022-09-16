from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional

from pydantic import root_validator

from powerfactory_utils.schema.base import Base

if TYPE_CHECKING:
    from typing import Any


class LoadModel(Base):
    """Load Representation Based on Polynomial Model.

    Load = Load0*(k_p*(U/U_0)^exp_p + k_i*(U/U_0)^exp_i + (1 - c_p - c_i)*(U/U_0)^exp_z)
    """

    name: Optional[str] = None
    c_p: float = 1
    c_i: float = 0
    c_z: float = 0
    exp_p: float = 0
    exp_i: float = 1
    exp_z: float = 2

    @root_validator
    def validate_range_c(cls, values: dict[str, Any]) -> dict[str, Any]:
        name = values["name"]

        # validate c_p
        c_p = values["c_p"]
        if not (0 <= c_p <= 1):
            raise ValueError(
                f"Load model '{name}': Component 'c_p' must be in the range between 0 and 1, but is {c_p}."
            )

        # validate c_i
        c_i = values["c_i"]
        if not (0 <= c_i <= 1):
            raise ValueError(
                f"Load model '{name}': Component 'c_i' must be in the range between 0 and 1, but is {c_i}."
            )

        if c_p + c_i > 1:
            raise ValueError(
                f"Load model '{name}': Sum of components must not raise 1, but sum of 'c_p' and 'c_i' is already {c_p + c_i}."
            )
        return values

    @root_validator
    def compute_c_z(cls, values: dict[str, Any]) -> dict[str, Any]:
        values["c_z"] = 1 - values["c_p"] - values["c_i"]
        return values
