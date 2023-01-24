# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.topology.characteristic import Characteristic
from powerfactory_utils.schema.topology.load_model import LoadModel


class ActivePower(Base):
    load_model: LoadModel | None = None
    characteristic: Characteristic | None = None

    class Config:
        frozen = True
