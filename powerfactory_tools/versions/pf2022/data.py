# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2024.
# :license: BSD 3-Clause

from __future__ import annotations

import dataclasses

from powerfactory_tools.base.data import PowerFactoryData as PowerFactoryDataBase


@dataclasses.dataclass
class PowerFactoryData(PowerFactoryDataBase): ...
