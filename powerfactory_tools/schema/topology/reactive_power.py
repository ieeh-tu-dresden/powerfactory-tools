# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.topology.load_model import LoadModel  # noqa: TCH001


class ReactivePower(Base):
    load_model: LoadModel | None = None
    external_controller_name: str | None = None  # Name of optional external load flow controller
