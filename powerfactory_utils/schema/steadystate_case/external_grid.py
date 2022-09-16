from __future__ import annotations

from typing import Optional

from powerfactory_utils.schema.base import Base


class ExternalGrid(Base):
    name: str
    u_0: Optional[float] = None
    phi_0: Optional[float] = None
    p_0: Optional[float] = None
    q_0: Optional[float] = None

    class Config:
        frozen = True
