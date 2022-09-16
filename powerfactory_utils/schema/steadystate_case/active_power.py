from __future__ import annotations

from powerfactory_utils.schema.base import Base


class ActivePower(Base):
    p_0: float  # actual active power

    class Config:
        frozen = True
