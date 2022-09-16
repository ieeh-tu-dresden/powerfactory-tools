from __future__ import annotations

from typing import Optional

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.topology.characteristic import Characteristic
from powerfactory_utils.schema.topology.load_model import LoadModel


class ActivePower(Base):
    load_model: Optional[LoadModel] = None
    characteristic: Optional[Characteristic] = None
