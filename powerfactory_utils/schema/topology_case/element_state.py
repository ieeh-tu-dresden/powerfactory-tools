from __future__ import annotations

from pydantic import Field

from powerfactory_utils.schema.base import Base


class ElementState(Base):
    class Config:
        frozen = True

    name: str
    disabled: bool = False
    open_switches: tuple[str, ...] = Field(default_factory=tuple)
