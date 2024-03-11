# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import typing as t

from base.types import IOpt
from base.types import ISym
from base.types import LoadLVPhaseConnectionType
from base.types import LoadPhaseConnectionType
from base.types import ModeInpMV
from base.types import PFRecap
from base.types import PowerFactoryTypes as PowerFactoryTypesBase
from base.types import PowerModelType

if t.TYPE_CHECKING:
    from collections.abc import Sequence


class PowerFactoryTypes(PowerFactoryTypesBase):
    class LoadTypeLV(PowerFactoryTypesBase.DataObject, t.Protocol):  # PFClassId.LOAD_TYPE_LV
        Smax: float  # maximum apparent power for a single residential unit, per default in kVA
        cosphi: float  # power factor
        ginf: float  # simultaneity factor

        iLodTyp: PowerModelType  # composite (ZIP) / exponent  # noqa: N815
        aP: float  # noqa: N815  # const. power part of the active power in relation to ZIP load model
        bP: float  # noqa: N815  # const. current part of the active power in relation to ZIP load model
        cP: float  # noqa: N815  # const. impedance part of the active power in relation to ZIP load model
        aQ: float  # noqa: N815  # const. power part of the reactive power in relation to ZIP load model
        bQ: float  # noqa: N815  # const. current part of the reactive power in relation to ZIP load model
        cQ: float  # noqa: N815  # const. impedance part of the reactive power in relation to ZIP load model

        eP: float  # noqa: N815  # exponent of the active power in relation to exponential load model
        eQ: float  # noqa: N815  # exponent of the reactive power in relation to exponential load model

    # LoadTypeMV is an equivalent of a distribution transformer
    class LoadTypeMV(PowerFactoryTypesBase.DataObject, t.Protocol):  # PFClassId.LOAD_TYPE_MV
        strn: float  # rated power, per default in MVA
        frnom: float  # nominal frequency
        tratio: float  # transformer ratio
        phtech: LoadPhaseConnectionType

        uktr: float  # short-circuit voltage in percentage (pos. seq.)
        pcutr: float  # cupper losses, per default in kW

        iZzero: bool  # 1 zero seq. impedance is given; 0 zero seq. impedance is not given  # noqa: N815
        uk0tr: float  # short-circuit voltage in percentage (zero. seq.)
        ur0tr: float  # real part of uk0tr

        pfe: float  # iron losses, per default in kW
        dutap: float  # additional voltage per tap changer step in percentage
        nntap0: int  # neutral position of tap changer
        ntpmn: int  # lowest position of tap changer
        ntpmx: int  # highest position of tap changer

        LodTyp: PowerModelType  # composite (ZIP) / exponent
        aP: float  # noqa: N815  # const. power part of the active power in relation to ZIP load model
        bP: float  # noqa: N815  # const. current part of the active power in relation to ZIP load model
        cP: float  # noqa: N815  # const. impedance part of the active power in relation to ZIP load model
        aQ: float  # noqa: N815  # const. power part of the reactive power in relation to ZIP load model
        bQ: float  # noqa: N815  # const. current part of the reactive power in relation to ZIP load model
        cQ: float  # noqa: N815  # const. impedance part of the reactive power in relation to ZIP load model

        eP: float  # noqa: N815  # exponent of the active power in relation to exponential load model
        eQ: float  # noqa: N815  # exponent of the reactive power in relation to exponential load model

    class LoadLVP(PowerFactoryTypesBase.LoadBase, t.Protocol):  # PFClassId.LOAD_LV_PART
        typ_id: PowerFactoryTypes.LoadTypeLV | None
        iopt_inp: IOpt
        elini: float
        cplinia: float
        slini: float
        plini: float
        qlini: float
        ilini: float
        coslini: float
        ulini: float
        pnight: float
        cSav: float  # noqa: N815
        cSmax: float  # noqa: N815
        ccosphi: float
        phtech: LoadLVPhaseConnectionType

    class LoadLV(PowerFactoryTypesBase.LoadBase3Ph, LoadLVP, t.Protocol):  # PFClassId.LOAD_LV
        typ_id: PowerFactoryTypes.LoadTypeLV | None
        i_sym: ISym
        lodparts: Sequence[PowerFactoryTypes.LoadLVP]
        phtech: LoadLVPhaseConnectionType

    class LoadMV(PowerFactoryTypesBase.LoadBase3Ph, t.Protocol):  # PFClassId.LOAD_MV
        typ_id: PowerFactoryTypes.LoadTypeMV | None
        mode_inp: ModeInpMV
        ci_sym: ISym
        elini: float
        cplinia: float
        sgini: float
        sginir: float
        sginis: float
        sginit: float
        pgini: float
        pginir: float
        pginis: float
        pginit: float
        cosgini: float
        cosginir: float
        cosginis: float
        cosginit: float
        gscale: float
        pfg_recap: PFRecap
        phtech: LoadPhaseConnectionType
