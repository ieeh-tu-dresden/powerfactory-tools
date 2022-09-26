from __future__ import annotations

from typing import Optional

from pydantic import validator

from powerfactory_utils.schema.base import Base
from powerfactory_utils.schema.steadystate_case.controller import Controller


class ReactivePower(Base):
    q_r: float  # actual reactive power (phase r)
    q_s: float  # actual reactive power (phase s)
    q_t: float  # actual reactive power (phase t)
    controller: Optional[Controller] = None

    @property
    def q(self) -> float:
        return self.q_r + self.q_s + self.q_t

    @property
    def symmetrical(self) -> bool:
        return self.q_r == self.q_s == self.q_t

    class Config:
        frozen = True

    @validator("controller")
    def validate_controller(cls, v: Controller) -> Controller:
        return v
