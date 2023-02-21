# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import pydantic  # noqa: TCH002

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.base import Meta
from powerfactory_tools.schema.topology.branch import Branch  # noqa: TCH001
from powerfactory_tools.schema.topology.external_grid import ExternalGrid  # noqa: TCH001
from powerfactory_tools.schema.topology.load import Load  # noqa: TCH001
from powerfactory_tools.schema.topology.node import Node  # noqa: TCH001
from powerfactory_tools.schema.topology.transformer import Transformer  # noqa: TCH001


class Topology(Base):
    meta: Meta
    branches: pydantic.conlist(Branch, unique_items=True)  # type: ignore[valid-type]
    nodes: pydantic.conlist(Node, unique_items=True)  # type: ignore[valid-type]
    loads: pydantic.conlist(Load, unique_items=True)  # type: ignore[valid-type]
    transformers: pydantic.conlist(Transformer, unique_items=True)  # type: ignore[valid-type]
    external_grids: pydantic.conlist(ExternalGrid, unique_items=True)  # type: ignore[valid-type]
