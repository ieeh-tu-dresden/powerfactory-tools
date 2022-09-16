from __future__ import annotations

from typing import Optional

from powerfactory_utils.schema.base import Base


class Transformer(Base):
    name: str
    tap_pos: Optional[int] = None  # actual tap position

    class Config:
        frozen = True
