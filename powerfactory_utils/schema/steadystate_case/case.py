from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Sequence

from loguru import logger
from pydantic.class_validators import validator

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.base import Meta
from powerfactory_utils.schema.steadystate_case.external_grid import ExternalGrid
from powerfactory_utils.schema.steadystate_case.load import Load
from powerfactory_utils.schema.steadystate_case.transformer import Transformer

if TYPE_CHECKING:
    from powerfactory_utils.schema.topology.topology import Topology


class Case(Base):
    meta: Meta
    loads: Sequence[Load]
    transformers: Sequence[Transformer]
    external_grids: Sequence[ExternalGrid]

    @validator("loads")
    def validate_loads(cls, v: Sequence[Load]) -> Sequence[Load]:
        return list(set(v))

    @validator("transformers")
    def validate_transformers(cls, v: Sequence[Transformer]) -> Sequence[Transformer]:
        return list(set(v))

    @validator("external_grids")
    def validate_external_grids(cls, v: Sequence[ExternalGrid]) -> Sequence[ExternalGrid]:
        return list(set(v))

    def verify_against_topology(self, topology: Topology) -> bool:
        logger.info("Verifying steadystate case ...")
        if topology.meta != self.meta:
            logger.error("Metadata does not match.")
            return False
        if not (n := len(self.loads)) == (n_t := len(topology.loads)):
            logger.error(f"Number of loads does not match. Is {n}, should be {n_t}.")
            return False
        if not (n := len(self.transformers)) == (n_t := len(topology.transformers)):
            logger.error(f"Number of transformers does not match. Is {n}, should be {n_t}.")
            return False
        if not (n := len(self.external_grids)) == (n_t := len(topology.external_grids)):
            logger.error(f"Number of external grids does not match. Is {n}, should be {n_t}.")
            return False

        load_names = [e.name for e in self.loads]
        for load in topology.loads:
            if (name := load.name) not in load_names:
                logger.error(f"Load {name} is not in steadystate case.")
                return False

        transformer_names = [e.name for e in self.transformers]
        for trafo in topology.transformers:
            if (name := trafo.name) not in transformer_names:
                logger.error(f"Transformer {name} is not in steadystate case.")
                return False

        external_grid_names = [e.name for e in self.external_grids]
        for ext_grid in topology.external_grids:
            if (name := ext_grid.name) not in external_grid_names:
                logger.error(f"External grid {name} is not in steadystate case.")
                return False
        logger.info("Verifying steadystate case was successful.")
        return True
