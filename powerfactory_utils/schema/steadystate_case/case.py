from __future__ import annotations

from typing import Sequence

from pydantic.class_validators import validator

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.base import Meta
from powerfactory_utils.schema.steadystate_case.external_grid import ExternalGrid
from powerfactory_utils.schema.steadystate_case.load import Load
from powerfactory_utils.schema.steadystate_case.transformer import Transformer


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
