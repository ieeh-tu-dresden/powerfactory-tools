# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.steadystate_case.active_power import ActivePower  # noqa: TCH001
from powerfactory_tools.schema.steadystate_case.reactive_power import ReactivePower  # noqa: TCH001


class Load(Base):  # including assets of type load and generator
    name: str
    active_power: ActivePower
    reactive_power: ReactivePower
