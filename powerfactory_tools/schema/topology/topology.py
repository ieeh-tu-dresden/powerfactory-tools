#! /usr/bin/python
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.base import Meta
from powerfactory_tools.schema.topology.branch import Branch  # noqa: TCH001
from powerfactory_tools.schema.topology.external_grid import ExternalGrid  # noqa: TCH001
from powerfactory_tools.schema.topology.load import Load  # noqa: TCH001
from powerfactory_tools.schema.topology.node import Node  # noqa: TCH001
from powerfactory_tools.schema.topology.transformer import Transformer  # noqa: TCH001


class Topology(Base):
    meta: Meta
    branches: set[Branch]
    nodes: set[Node]
    loads: set[Load]
    transformers: set[Transformer]
    external_grids: set[ExternalGrid]

    class Config:
        frozen = True
