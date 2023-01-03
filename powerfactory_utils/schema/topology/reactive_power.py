# -*- coding: utf-8 -*-

from __future__ import annotations

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.topology.load_model import LoadModel


class ReactivePower(Base):
    load_model: LoadModel | None = None
    external_controller_name: str | None = None  # Name of optional external load flow controller
