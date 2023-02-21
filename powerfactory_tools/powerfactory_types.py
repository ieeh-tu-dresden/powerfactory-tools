# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal
from typing import Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


class CtrlMode:  # 0:Voltage Control; 1:Reactive Power Control; 2:Cosphi Control; 3:Tanphi Control
    PowAct = 0
    PowReact = 1
    Cosphi = 2
    Tanphi = 3


class CosphiChar:  # 0:const. Cosphi; 1:Cosphi(P); 2:Cosphi(U)
    const = 0
    U = 1
    P = 2


class PowReactChar:  # 0:const. Q; 1:Q(U); 2: Q(P)
    const = 0
    U = 1
    P = 2


class IOpt:  # 0:const. Q; 1:Q(U); 2: Q(P)
    SCosphi = 0
    PCosphi = 1
    UICosphi = 2
    ECosphi = 3


class PowerFactoryTypes:
    ModeInpLoad = Literal["DEF", "PQ", "PC", "IC", "SC", "QC", "IP", "SP", "SQ"]
    ModeInpGen = Literal["DEF", "PQ", "PC", "SC", "QC", "SP", "SQ"]
    ModeInpMV = Literal["PC", "SC", "EC"]
    IOptInp = Literal[0, 1, 2]  # 0:const. Q; 1:Q(U); 2: Q(P)
    PFRecap = Literal[0, 1]
    PhTechLoad = Literal[0, 2, 3, 4, 5, 7, 8, 9]  # Phase Connection Type cfg. schema.load
    PhTechGen = Literal[0, 1, 2, 3, 4]  # Phase Connection Type cfg. schema.load
    TrfVector = Literal["Y", "YN", "Z", "ZN", "D"]
    TrfVectorGroup = Literal[
        "Dd0",
        "Yy0",
        "YNy0",
        "Yyn0",
        "YNyn0",
        "Dz0",
        "Dzn0",
        "Zd0",
        "ZNd0",
        "Dy5",
        "Dyn5",
        "Yd5",
        "YNd5",
        "Yz5",
        "YNz5",
        "Yzn5",
        "YNzn5",
        "Dd6",
        "Yy6",
        "YNy6",
        "Yyn6",
        "YNyn6",
        "Dz6",
        "Dzn6",
        "Zd6",
        "ZNd6",
        "Dy11",
        "Dyn11",
        "Yd11",
        "YNd11",
        "Yz11",
        "YNz11",
        "Yzn11",
        "YNzn11",
    ]
    TrfPhaseTechnology = Literal[1, 2, 3]  # Single core for each Phase or three phases combined
    TrfTapSide = Literal[0, 1, 2, 3]  # Transformer side of tap changer
    QCtrlTypes = Literal["constv", "vdroop", "idroop", "constq", "qpchar", "qvchar", "constc", "cpchar"]
    BusType = Literal["SL", "PV", "PQ"]
    GenSystemType = Literal[
        "coal",
        "oil",
        "gas",
        "dies",  # diesel generation
        "nuc",  # nuclear generation
        "hydr",  # hydro generation
        "pump",  # pump storage
        "wgen",  # wind generation
        "bgas",  # bio gas
        "sol",  # solar generation
        "othg",  # other
        "pv",  # pv cell generation
        "reng",  # renewable energies
        "fc",  # fuel cell
        "peat",  # biomass/peat
        "stg",  # static generator
        "hvdc",  # hvdc station
        "rpc",  # reactive power compensation
        "stor",  # storage
        "net",  # external grid
    ]
    MetricPrefix = Literal["a", "f", "p", "n", "u", "m", "", "k", "M", "G", "T", "P", "E"]
    Currency = Literal[
        "USD",
        "EUR",
        "JPY",
        "GBP",
        "AUD",
        "CAD",
        "CHF",
        "CNY",
        "SEK",
        "MXN",
        "NZD",
        "SGD",
        "HKD",
        "NOK",
        "KRW",
        "TRY",
        "INR",
        "RUB",
        "BRL",
        "ZAR",
        "CLP",
    ]

    class DataObject(Protocol):
        loc_name: str
        fold_id: PowerFactoryTypes.DataObject | None

        def GetContents(  # noqa: N802
            self,
            name: str,
            recursive: bool = False,  # noqa: FBT001, FBT002
            /,
        ) -> Sequence[PowerFactoryTypes.DataObject]:
            ...

        def CreateObject(  # noqa: N802
            self,
            class_name: str,
            name: str | int | None,
            /,
        ) -> PowerFactoryTypes.DataObject | None:
            ...

        def Delete(self) -> int:  # noqa: N802
            ...

    class GridDiagram(DataObject, Protocol):
        ...

    class Graph(DataObject, Protocol):
        sSymName: str  # noqa: N815
        pDataObj: PowerFactoryTypes.DataObject | None  # noqa: N815
        rCenterX: float  # noqa: N815
        rCenterY: float  # noqa: N815
        rSizeX: float  # noqa: N815
        rSizeY: float  # noqa: N815
        iRot: int  # noqa: N815
        iLevel: int  # noqa: N815
        iCol: int  # noqa: N815
        iCollapsed: bool  # noqa: N815
        iIndLS: int  # noqa: N815
        iVis: bool  # noqa: N815

    class Project(DataObject, Protocol):
        pPrjSettings: PowerFactoryTypes.ProjectSettings  # noqa: N815

        def Deactivate(self) -> bool:  # noqa: N802
            ...

    class Scenario(DataObject, Protocol):
        def Activate(self) -> bool:  # noqa: N802
            ...

        def Deactivate(self) -> bool:  # noqa: N802
            ...

    class StudyCase(DataObject, Protocol):
        def Activate(self) -> bool:  # noqa: N802
            ...

        def Deactivate(self) -> bool:  # noqa: N802
            ...

    class ProjectSettings(DataObject, Protocol):
        extDataDir: PowerFactoryTypes.DataDir  # noqa: N815
        ilenunit: Literal[0, 1, 2]
        clenexp: PowerFactoryTypes.MetricPrefix  # Lengths
        cspqexp: PowerFactoryTypes.MetricPrefix  # Loads etc.
        cspqexpgen: PowerFactoryTypes.MetricPrefix  # Generators etc.
        currency: PowerFactoryTypes.Currency

    class UnitConversionSetting(DataObject, Protocol):
        filtclass: Sequence[str]
        filtvar: str
        digunit: str
        cdigexp: PowerFactoryTypes.MetricPrefix
        userunit: str
        cuserexp: PowerFactoryTypes.MetricPrefix
        ufacA: float  # noqa: N815
        ufacB: float  # noqa: N815

    class DataDir(DataObject, Protocol):
        ...

    class Substation(DataObject, Protocol):
        ...

    class LoadType(DataObject, Protocol):
        loddy: float  # portion of dynamic part of ZIP load model in RMS simulation (100 = 100% dynamic)
        systp: bool  # 0:AC; 1:DC
        phtech: PowerFactoryTypes.PhTechLoad  # phase connection: [0, 2, 3, 4, 5, 7, 8, 9] cfg. schema.load.PhaseConnectionType

        aP: float  # noqa: N815  # a-portion of the active power in relation to ZIP load model
        bP: float  # noqa: N815  # b-portion of the active power in relation to ZIP load model
        cP: float  # noqa: N815  # c-portion of the active power in relation to ZIP load model
        kpu0: float  # exponent of the a-portion of the active power in relation to ZIP load model
        kpu1: float  # exponent of the b-portion of the active power in relation to ZIP load model
        kpu: float  # exponent of the c-portion of the active power in relation to ZIP load model

        aQ: float  # noqa: N815  # a-portion of the reactive power in relation to ZIP load model
        bQ: float  # noqa: N815  # b-portion of the reactive power in relation to ZIP load model
        cQ: float  # noqa: N815  # c-portion of the reactive power in relation to ZIP load model
        kqu0: float  # exponent of the a-portion of the reactive power in relation to ZIP load model
        kqu1: float  # exponent of the b-portion of the reactive power in relation to ZIP load model
        kqu: float  # exponent of the c-portion of the reactive power in relation to ZIP load model

    class LineType(DataObject, Protocol):
        uline: float  # rated voltage (kV)
        sline: float  # rated current (kA) when installed in soil
        InomAir: float  # rated current (kA) when installed in air
        rline: float  # resistance (Ohm/km) positive sequence components
        rline0: float  # resistance (Ohm/km) zero sequence components
        xline: float  # reactance (Ohm/km) positive sequence components
        xline0: float  # reactance (Ohm/km) zero sequence components
        gline: float  # conductance (µS/km) positive sequence components
        gline0: float  # conductance (µS/km) zero sequence components
        bline: float  # susceptance (µS/km) positive sequence components
        bline0: float  # susceptance (µS/km) zero sequence components
        systp: bool  # 0:AC; 1:DC
        frnom: float  # nominal frequency the values x and b apply

    class Transformer2WType(DataObject, Protocol):
        vecgrp: PowerFactoryTypes.TrfVectorGroup
        dutap: float
        phitr: float
        ntpmn: int
        ntpmx: int
        nntap0: int
        utrn_l: float
        utrn_h: float
        pfe: float
        curmg: float
        pcutr: float
        strn: float
        uktr: float
        zx0hl_n: float
        rtox0_n: float
        r1pu: float
        r0pu: float
        x1pu: float
        x0pu: float
        tr2cn_l: PowerFactoryTypes.TrfVector
        tr2cn_h: PowerFactoryTypes.TrfVector
        nt2ag: float
        nt2ph: PowerFactoryTypes.TrfPhaseTechnology
        tap_side: PowerFactoryTypes.TrfTapSide
        itapch: int
        itapch2: int

    class Transformer3WType(DataObject, Protocol):
        ...

    class SwitchType(DataObject, Protocol):
        Inom: float
        R_on: float
        X_on: float

    class Coupler(DataObject, Protocol):
        bus1: PowerFactoryTypes.StationCubicle | None
        bus2: PowerFactoryTypes.StationCubicle | None
        typ_id: PowerFactoryTypes.SwitchType | None
        cpSubstat: PowerFactoryTypes.Substation | None  # noqa: N815
        isclosed: bool  # 0:open; 1:closed
        desc: Sequence[str]

    class Grid(DataObject, Protocol):
        def Activate(self) -> bool:  # noqa: N802
            ...

        def Deactivate(self) -> bool:  # noqa: N802
            ...

    class LineBase(DataObject, Protocol):
        cDisplayName: str  # noqa: N815
        desc: Sequence[str]
        outserv: bool

    class Terminal(DataObject, Protocol):
        cDisplayName: str  # noqa: N815
        desc: Sequence[str]
        uknom: float
        iUsage: Literal[0, 1, 2]  # noqa: N815  # 0:bus bar; 1:junction node; 2:internal node
        outserv: bool
        cpSubstat: PowerFactoryTypes.Substation | None  # noqa: N815
        cubics: Sequence[PowerFactoryTypes.StationCubicle]

    class StationCubicle(DataObject, Protocol):
        cterm: PowerFactoryTypes.Terminal
        obj_id: PowerFactoryTypes.Line | PowerFactoryTypes.Element | None

    class Transformer2W(LineBase, Protocol):
        buslv: PowerFactoryTypes.StationCubicle | None
        bushv: PowerFactoryTypes.StationCubicle | None
        ntnum: int
        typ_id: PowerFactoryTypes.Transformer2WType | None
        nntap: int

    class Transformer3W(LineBase, Protocol):
        buslv: PowerFactoryTypes.StationCubicle | None
        busmv: PowerFactoryTypes.StationCubicle | None
        bushv: PowerFactoryTypes.StationCubicle | None
        nt3nm: int
        typ_id: PowerFactoryTypes.Transformer3WType | None
        n3tapl: int
        n3tapm: int
        n3taph: int

    class ControllerBase(DataObject, Protocol):
        c_pmod: PowerFactoryTypes.CompoundModel | None

    class SecondaryController(ControllerBase, Protocol):
        ...

    class StationController(ControllerBase, Protocol):
        i_ctrl: Literal[0, 1, 2, 3]  # 0:Voltage Control; 1:Reactive Power Control; 2:Cosphi Control; 3:Tanphi Control
        qu_char: Literal[0, 1, 2]  # 0:const. Q; 1:Q(U); 2: Q(P)
        qsetp: float
        iQorient: Literal[0, 1]  # noqa: N815  # 0:+Q; 1:-Q
        refbar: PowerFactoryTypes.Terminal
        Srated: float
        ddroop: float
        Qmin: float
        Qmax: float
        udeadblow: float
        udeadbup: float
        cosphi_char: Literal[0, 1, 2]  # 0:const. Cosphi; 1:Cosphi(P); 2:Cosphi(U)
        pfsetp: float
        pf_recap: PowerFactoryTypes.PFRecap
        tansetp: float

    class CompoundModel(DataObject, Protocol):
        ...

    class Element(DataObject, Protocol):
        desc: Sequence[str]
        pf_recap: PowerFactoryTypes.PFRecap  # 0:over excited; 1:under excited
        bus1: PowerFactoryTypes.StationCubicle | None
        scale0: float

    class GeneratorBase(Element, Protocol):
        ngnum: int
        sgn: float
        cosn: float
        pgini: float
        qgini: float
        cosgini: float
        pf_recap: PowerFactoryTypes.PFRecap  # 0:over excited; 1:under excited
        Kpf: float
        ddroop: float
        Qfu_min: float
        Qfu_max: float
        udeadblow: float
        udeadbup: float
        outserv: bool
        av_mode: PowerFactoryTypes.QCtrlTypes
        mode_inp: PowerFactoryTypes.ModeInpGen
        phtech: PowerFactoryTypes.PhTechGen
        sgini_a: float
        pgini_a: float
        qgini_a: float
        cosgini_a: float
        pf_recap_a: PowerFactoryTypes.PFRecap  # 0:over excited; 1:under excited
        scale0_a: float
        c_pstac: PowerFactoryTypes.StationController | None
        c_pmod: PowerFactoryTypes.CompoundModel | None  # Compound Parent Model/Template

    class Generator(GeneratorBase, Protocol):
        cCategory: PowerFactoryTypes.GenSystemType  # noqa: N815
        c_psecc: PowerFactoryTypes.SecondaryController | None

    class PVSystem(GeneratorBase, Protocol):
        uk: float
        Pcu: float

    class LoadBase(Element, Protocol):
        slini: float
        slinir: float
        slinis: float
        slinit: float
        plini: float
        plinir: float
        plinis: float
        plinit: float
        qlini: float
        qlinir: float
        qlinis: float
        qlinit: float
        ilini: float
        ilinir: float
        ilinis: float
        ilinit: float
        coslini: float
        coslinir: float
        coslinis: float
        coslinit: float
        outserv: bool
        typ_id: PowerFactoryTypes.LoadType | None

    class Load(LoadBase, Protocol):
        mode_inp: PowerFactoryTypes.ModeInpLoad
        """DEF: Default;
        PQ: P, Q
        PC: P, cosphi
        IC: I, cosphi
        SC: S, cosphi
        QC: Q, cosphi
        IP: I, P
        SP: S, P
        SQ: S, Q"""

        i_sym: bool  # 0:symmetrical; 1:asymmetrical
        u0: float

    class LoadLVP(DataObject, Protocol):
        iopt_inp: PowerFactoryTypes.IOptInp  # 0:S,cosphi; 1:P,cosphi,2:U,I,cosphi; 3:E,cosphi
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
        ccosphi: float

    class LoadLV(LoadBase, LoadLVP, Protocol):
        i_sym: bool  # 0:symmetrical; 1:asymmetrical
        lodparts: Sequence[PowerFactoryTypes.LoadLVP]

    class LoadMV(LoadBase, Protocol):
        mode_inp: PowerFactoryTypes.ModeInpMV
        ci_sym: bool  # 0:symmetrical; 1:asymmetrical
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
        pfg_recap: PowerFactoryTypes.PFRecap  # 0:over excited; 1:under excited

    class Switch(DataObject, Protocol):
        fold_id: PowerFactoryTypes.StationCubicle
        isclosed: bool  # 0:open; 1:closed

    class Fuse(DataObject, Protocol):
        ...

    class Line(LineBase, Protocol):
        bus1: PowerFactoryTypes.StationCubicle | None
        bus2: PowerFactoryTypes.StationCubicle | None
        nlnum: int  # no. of parallel lines
        dline: float  # line length (km)
        fline: float  # installation factor
        inAir: bool  # noqa: N815 # 0:soil; 1:air
        Inom_a: float  # nominal current (actual)
        typ_id: PowerFactoryTypes.LineType | None

    class ExternalGrid(DataObject, Protocol):
        bustp: PowerFactoryTypes.BusType
        bus1: PowerFactoryTypes.StationCubicle | None
        desc: Sequence[str]
        usetp: float  # in p.u.
        pgini: float  # in MW
        qgini: float  # in Mvar
        phiini: float  # in deg
        snss: float  # in MVA
        snssmin: float  # in MVA
        outserv: bool

    class Script(Protocol):
        def SetExternalObject(self, name: str, value: PowerFactoryTypes.DataObject) -> int:  # noqa: N802
            ...

        def Execute(self) -> int:  # noqa: N802
            ...

    class Application(Protocol):
        def ActivateProject(self, name: str) -> int:  # noqa: N802
            ...

        def GetActiveProject(self) -> PowerFactoryTypes.Project:  # noqa: N802
            ...

        def GetActiveScenario(self) -> PowerFactoryTypes.Scenario | None:  # noqa: N802
            ...

        def GetProjectFolder(self, name: str) -> PowerFactoryTypes.DataObject:  # noqa: N802
            ...

        def PostCommand(self, command: Literal["exit"]) -> None:  # noqa: N802
            ...

    class PowerFactoryModule(Protocol):
        ExitError: tuple[type[Exception], ...]

        def GetApplicationExt(  # noqa: N802
            self,
            username: str | None = None,
            password: str | None = None,
            commandLineArguments: str | None = None,  # noqa: N803
        ) -> PowerFactoryTypes.Application:
            ...
