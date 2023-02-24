# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import pydantic

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.topology.load import validate_symmetry
from powerfactory_tools.schema.topology.load import validate_total


class ActivePower(Base):
    value: float  # actual active power (three-phase)
    value_a: float  # actual active power (phase a)
    value_b: float  # actual active power (phase b)
    value_c: float  # actual active power (phase c)
    is_symmetrical: bool

    @pydantic.root_validator(skip_on_failure=True)
    def _validate_symmetry(cls, values: dict[str, float]) -> dict[str, float]:
        return validate_symmetry(values)

    @pydantic.root_validator(skip_on_failure=True)
    def _validate_total(cls, values: dict[str, float]) -> dict[str, float]:
        return validate_total(values)
