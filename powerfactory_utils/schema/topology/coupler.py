from __future__ import annotations

from powerfactory_utils.schema.base import Base


class Coupler(Base):
    element: str
    node: str
    state: bool  # 0:opened; 1:closed
