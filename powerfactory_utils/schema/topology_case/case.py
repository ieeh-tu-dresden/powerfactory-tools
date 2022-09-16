from __future__ import annotations

from typing import Sequence

from pydantic.class_validators import validator

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.base import Meta
from powerfactory_utils.schema.topology_case.element_state import ElementState


class Case(Base):
    meta: Meta
    elements: Sequence[ElementState]

    @validator("elements")
    def validate_elements(cls, v: Sequence[ElementState]) -> Sequence[ElementState]:
        return list(set(v))
