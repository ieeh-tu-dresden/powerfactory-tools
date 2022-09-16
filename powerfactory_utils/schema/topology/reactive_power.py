from __future__ import annotations

from typing import Optional

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.topology.load_model import LoadModel


class ReactivePower(Base):
    load_model: Optional[LoadModel] = None
    external_controller_name: Optional[str] = None  # Name of optional external load flow controller
