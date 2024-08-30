# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2024.
# :license: BSD 3-Clause

from __future__ import annotations

import dataclasses
import typing as t

if t.TYPE_CHECKING:
    import collections.abc as cabc
    import datetime as dt

    from powerfactory_tools.versions.pf2024.types import PowerFactoryTypes as PFTypes


@dataclasses.dataclass
class PowerFactoryData:
    date: dt.date
    project_name: str
    grid_name: str
    external_grids: cabc.Sequence[PFTypes.ExternalGrid]
    terminals: cabc.Sequence[PFTypes.Terminal]
    lines: cabc.Sequence[PFTypes.Line]
    transformers_2w: cabc.Sequence[PFTypes.Transformer2W]
    transformers_3w: cabc.Sequence[PFTypes.Transformer3W]
    loads: cabc.Sequence[PFTypes.Load]
    loads_lv: cabc.Sequence[PFTypes.LoadLV]
    loads_mv: cabc.Sequence[PFTypes.LoadMV]
    generators: cabc.Sequence[PFTypes.Generator]
    pv_systems: cabc.Sequence[PFTypes.PVSystem]
    couplers: cabc.Sequence[PFTypes.Coupler]
    switches: cabc.Sequence[PFTypes.Switch]
    bfuses: cabc.Sequence[PFTypes.BFuse]
    efuses: cabc.Sequence[PFTypes.EFuse]
    ac_current_sources: cabc.Sequence[PFTypes.AcCurrentSource]
    ac_voltage_sources: cabc.Sequence[PFTypes.AcVoltageSource]
    shunts: cabc.Sequence[PFTypes.Shunt]
