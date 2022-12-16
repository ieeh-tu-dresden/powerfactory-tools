from __future__ import annotations

from pydantic import Field

from powerfactory_utils.schema.base import Base


class ElementState(Base):
    class Config:
        frozen = True

    name: str
    active: bool  # 0:off/opened; 1:on/closed
    disabled: bool = False
    open_switches: list[str] = Field(default_factory=list)
