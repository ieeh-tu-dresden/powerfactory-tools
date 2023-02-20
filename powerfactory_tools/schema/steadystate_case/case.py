# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

import pydantic  # noqa: TCH002
from loguru import logger

from powerfactory_tools.schema.base import Base
from powerfactory_tools.schema.base import Meta
from powerfactory_tools.schema.steadystate_case.external_grid import ExternalGrid  # noqa: TCH001
from powerfactory_tools.schema.steadystate_case.load import Load  # noqa: TCH001
from powerfactory_tools.schema.steadystate_case.transformer import Transformer  # noqa: TCH001

if TYPE_CHECKING:
    from powerfactory_tools.schema.topology.topology import Topology


class Case(Base):
    meta: Meta
    loads: pydantic.conlist(Load, unique_items=True)  # type: ignore[valid-type]
    transformers: pydantic.conlist(Transformer, unique_items=True)  # type: ignore[valid-type]
    external_grids: pydantic.conlist(ExternalGrid, unique_items=True)  # type: ignore[valid-type]

    def is_valid_topology(self, topology: Topology) -> bool:
        logger.info("Verifying steadystate case ...")
        if topology.meta != self.meta:
            logger.error("Metadata does not match.")
            return False

        if not self._is_proper_element_number(topology):
            return False

        if not self._is_proper_elements(topology):
            return False

        logger.info("Verifying steadystate case was successful.")
        return True

    def _is_proper_element_number(self, topology: Topology) -> bool:
        if len(self.loads) != len(topology.loads):
            logger.error(
                "Number of loads does not match. Is {n_act}, should be {n_ref}.",
                n_act=len(self.loads),
                n_ref=len(topology.loads),
            )
            return False

        if len(self.transformers) != len(topology.transformers):
            logger.error(
                "Number of transformers does not match. Is {n_act}, should be {n_ref}.",
                n_act=len(self.transformers),
                n_ref=len(topology.transformers),
            )
            return False

        if len(self.external_grids) != len(topology.external_grids):
            logger.error(
                "Number of external grids does not match. Is {n_act}, should be {n_ref}.",
                n_act=len(self.external_grids),
                n_ref=len(topology.external_grids),
            )
            return False

        return True

    def _is_proper_elements(self, topology: Topology) -> bool:
        if not self._is_proper_loads(topology):
            return False

        if not self._is_proper_transformers(topology):
            return False

        return self._is_proper_external_grids(topology)

    def _is_proper_loads(self, topology: Topology) -> bool:
        load_names = [e.name for e in self.loads]
        for load in topology.loads:
            if load.name not in load_names:
                logger.error("Load {load_name} is not in steadystate case.", load_name=load.name)
                return False

        return True

    def _is_proper_transformers(self, topology: Topology) -> bool:
        transformer_names = [e.name for e in self.transformers]
        for trafo in topology.transformers:
            if trafo.name not in transformer_names:
                logger.error("Transformer {trafo_name} is not in steadystate case.", trafo_name=trafo.name)
                return False

        return True

    def _is_proper_external_grids(self, topology: Topology) -> bool:
        external_grid_names = [e.name for e in self.external_grids]
        for ext_grid in topology.external_grids:
            if ext_grid.name not in external_grid_names:
                logger.error(
                    "External grid {ext_grid_name} is not in steadystate case.",
                    ext_grid_name=ext_grid.name,
                )
                return False

        return True
