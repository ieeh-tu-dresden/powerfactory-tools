from __future__ import annotations

from typing import Sequence

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.base import Meta
from powerfactory_utils.schema.topology.branch import Branch
from powerfactory_utils.schema.topology.external_grid import ExternalGrid
from powerfactory_utils.schema.topology.load import Load
from powerfactory_utils.schema.topology.node import Node
from powerfactory_utils.schema.topology.transformer import Transformer


class Topology(Base):
    meta: Meta
    branches: Sequence[Branch]
    nodes: Sequence[Node]
    loads: Sequence[Load]
    transformers: Sequence[Transformer]
    external_grids: Sequence[ExternalGrid]
