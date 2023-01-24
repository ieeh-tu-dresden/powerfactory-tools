# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.base import Meta
from powerfactory_utils.schema.topology.branch import Branch
from powerfactory_utils.schema.topology.external_grid import ExternalGrid
from powerfactory_utils.schema.topology.load import Load
from powerfactory_utils.schema.topology.node import Node
from powerfactory_utils.schema.topology.transformer import Transformer


class Topology(Base):
    meta: Meta
    branches: set[Branch]
    nodes: set[Node]
    loads: set[Load]
    transformers: set[Transformer]
    external_grids: set[ExternalGrid]

    class Config:
        frozen = True
