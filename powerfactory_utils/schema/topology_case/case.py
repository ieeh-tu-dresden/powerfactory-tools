# -*- coding: utf-8 -*-

from __future__ import annotations

from collections.abc import Sequence

from pydantic.class_validators import validator

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.base import Meta
from powerfactory_utils.schema.topology_case.element_state import ElementState


class Case(Base):
    meta: Meta
    elements: Sequence[ElementState]

    @validator("elements")
    def validate_elements(cls, value: Sequence[ElementState]) -> Sequence[ElementState]:  # noqa: N805, U100
        return list(set(value))
