from __future__ import annotations

from typing import Optional

from pydantic import validator

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.steadystate_case.controller import Controller


class ReactivePower(Base):
    q_0: float  # Initial reactive power resp. the actual reactive power for load flow
    controller: Optional[Controller] = None

    class Config:
        frozen = True

    @validator("controller")
    def validate_controller(cls, v: Controller) -> Controller:
        return v
