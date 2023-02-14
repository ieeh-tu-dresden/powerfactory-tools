# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.base import Meta
from powerfactory_tools.schema.topology_case.element_state import ElementState  # noqa: TCH001


class Case(Base):
    meta: Meta
    elements: set[ElementState]

    class Config:
        frozen = True
