# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from pydantic import root_validator

from powerfactory_utils.schema.base import Base


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

    @root_validator
    def validate_range_c(cls, load_model: LoadModel) -> LoadModel:  # noqa: U100
        name = load_model.name

        # validate c_p
        c_p = load_model.c_p
        if not (0 <= c_p <= 1):
            raise ValueError(f"Load model {name!r}: Components must be in the range between 0 and 1, but {c_p=}.")

        # validate c_i
        c_i = load_model.c_i
        if not (0 <= c_i <= 1):
            raise ValueError(f"Load model {name!r}: Components must be in the range between 0 and 1, but {c_i=}.")

        if c_p + c_i > 1:
            raise ValueError(f"Load model {name!r}: Sum of components must not exceed 1, but {(c_p + c_i)=}.")

        return load_model

    @root_validator
    def compute_c_z(cls, load_model: LoadModel) -> LoadModel:  # noqa: U100
        load_model.c_z = 1 - load_model.c_p - load_model.c_i
        return load_model
