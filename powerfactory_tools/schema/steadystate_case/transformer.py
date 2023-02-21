# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from powerfactory_tools.schema.base import Base


class Transformer(Base):
    name: str
    tap_pos: int | None = None  # actual tap position
