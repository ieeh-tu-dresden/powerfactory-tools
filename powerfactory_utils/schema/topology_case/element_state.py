from __future__ import annotations

from typing import Optional

from powerfactory_utils.schema.base import Base


class ElementState(Base):
    class Config:
        frozen = True

    name: str
    active: bool  # 0:off/opened; 1:on/closed
    node: Optional[str] = None
