from __future__ import annotations

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.steadystate_case.active_power import ActivePower
from powerfactory_utils.schema.steadystate_case.reactive_power import ReactivePower


class Load(Base):  # including assets of type load and generator
    name: str
    active_power: ActivePower
    reactive_power: ReactivePower

    class Config:
        frozen = True
