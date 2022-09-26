from __future__ import annotations

from powerfactory_utils.schema.base import Base


class ActivePower(Base):
    p_r: float  # actual active power (phase r)
    p_s: float  # actual active power (phase s)
    p_t: float  # actual active power (phase t)

    @property
    def p(self) -> float:
        return self.p_r + self.p_s + self.p_t

    @property
    def symmetrical(self) -> bool:
        return self.p_r == self.p_s == self.p_t

    class Config:
        frozen = True
