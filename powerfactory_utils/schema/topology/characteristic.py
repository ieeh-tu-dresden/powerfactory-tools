from __future__ import annotations

from typing import Optional

from powerfactory_utils.schema.base import Base


class Characteristic(Base):
    description: Optional[str] = None
