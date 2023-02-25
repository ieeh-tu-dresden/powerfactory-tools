# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pydantic

from powerfactory_tools.schema.base import Base

if TYPE_CHECKING:
    from typing import Any


class LoadModel(Base):
    """Load Representation Based on Polynomial Model.

    Load = Load0*(k_p*(U/U_0)^exp_p + k_i*(U/U_0)^exp_i + (1 - c_p - c_i)*(U/U_0)^exp_z)
    """

    name: str | None = None
    c_p: float = 1
    c_i: float = 0
    c_z: float = 0
    exp_p: float = 0
    exp_i: float = 1
    exp_z: float = 2

    @pydantic.root_validator
    def validate_range_c(cls, values: dict[str, Any]) -> dict[str, Any]:
        name = values["name"]

        # validate c_p
        c_p = values["c_p"]
        if not (0 <= c_p <= 1):
            msg = f"Load model {name!r}: Components must be in the range between 0 and 1, but {c_p=}."
            raise ValueError(msg)

        # validate c_i
        c_i = values["c_i"]
        if not (0 <= c_i <= 1):
            msg = f"Load model {name!r}: Components must be in the range between 0 and 1, but {c_i=}."
            raise ValueError(msg)

        if c_p + c_i > 1:
            msg = f"Load model {name!r}: Sum of components must not exceed 1, but {(c_p + c_i)=}."
            raise ValueError(msg)

        return values

    @pydantic.root_validator
    def compute_c_z(cls, values: dict[str, Any]) -> dict[str, Any]:
        values["c_z"] = 1 - values["c_p"] - values["c_i"]
        return values
