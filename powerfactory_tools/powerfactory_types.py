# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import enum
from typing import TYPE_CHECKING
from typing import Literal
from typing import Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


class LocalQCtrlMode(enum.Enum):
    U_CONST = "constv"
    COSPHI_CONST = "constc"
    Q_CONST = "constq"
    Q_U = "qvchar"
    Q_P = "qpchar"
    COSPHI_P = "cpchar"
    U_Q_DROOP = "vdroop"
    U_I_DROOP = "idroop"


class CtrlMode(enum.IntEnum):
    U = 0
    Q = 1
    COSPHI = 2
    TANPHI = 3


class CosphiChar(enum.IntEnum):
    CONST = 0
    P = 1
    U = 2


class QChar(enum.IntEnum):
    CONST = 0
    U = 1
    P = 2


class IOpt(enum.IntEnum):
    S_COSPHI = 0
    P_COSPHI = 1
    U_I_COSPHI = 2
    E_COSPHI = 3


class CtrlVoltageRef(enum.IntEnum):
    POS_SEQ = 0  # positive sequence value of voltage
    AVG = 1  # average value of voltage
    A = 2
    B = 3
    C = 4
    AB = 5
    BC = 6
    CA = 7


class GeneratorPhaseConnectionType(enum.IntEnum):
    THREE_PH_D = 0
    THREE_PH_PH_E = 1
    ONE_PH_PH_E = 2
    ONE_PH_PH_N = 3
    ONE_PH_PH_PH = 4


class LoadPhaseConnectionType(enum.IntEnum):
    THREE_PH_D = 0
    THREE_PH_PH_E = 2
    THREE_PH_YN = 3
    TWO_PH_PH_E = 4
    TWO_PH_YN = 5
    ONE_PH_PH_PH = 7
    ONE_PH_PH_N = 8
    ONE_PH_PH_E = 9


class PFRecap(enum.IntEnum):
    OE = 0
    UE = 1


class QOrient(enum.IntEnum):
    Q_POS = 0
    Q_NEG = 1


class NodeType(enum.IntEnum):
    BUS_BAR = 0
    JUNCTION_NODE = 1
    INTERNAL_NODE = 2


class QCtrlTypes(enum.Enum):
    U_CONST = "constv"
    VDROOP = "vdroop"
    IDROOP = "idroop"
    Q_CONST = "constq"
    Q_P = "qpchar"
    Q_U = "qvchar"
    COSPHI_CONST = "constc"
    COSPHI_P = "cpchar"


class ModeInpLoad(enum.Enum):
    DEF = "DEF"
    PQ = "PQ"
    PC = "PC"
    IC = "IC"
    SC = "SC"
    QC = "QC"
    IP = "IP"
    SP = "SP"
    SQ = "SQ"


class ModeInpGen(enum.Enum):
    DEF = "DEF"
    PQ = "PQ"
    PC = "PC"
    SC = "SC"
    QC = "QC"
    SP = "SP"
    SQ = "SQ"


class ModeInpMV(enum.Enum):
    PC = "PC"
    SC = "SC"
    EC = "EC"


class BusType(enum.Enum):
    SL = "SL"
    PV = "PV"
    PQ = "PQ"


class Vector(enum.Enum):
    Y = "Y"
    YN = "YN"
    Z = "Z"
    ZN = "ZN"
    D = "D"


class GeneratorSystemType(enum.Enum):
    COAL = "coal"
    OIL = "oil"
    GAS = "gas"
    DIESEL = "dies"
    NUCLEAR = "nuc"
    HYDRO = "hydr"
    PUMP_STORAGE = "pump"
    WIND = "wgen"
    BIOGAS = "bgas"
    SOLAR = "sol"
    PV = "pv"
    RENEWABLE_ENERGY = "reng"
    FUELCELL = "fc"
    PEAT = "peat"
    STAT_GEN = "stg"
    HVDC = "hvdc"
    REACTIVE_POWER_COMPENSATOR = "rpc"
    BATTERY_STORAGE = "stor"
    EXTERNAL_GRID_EQUIVALENT = "net"
    OTHER = "othg"


class VectorGroup(enum.Enum):
    Dd0 = "Dd0"
    Yy0 = "Yy0"
    YNy0 = "Ny0"
    Yyn0 = "Yyn0"
    YNyn0 = "Nyn0"
    Dz0 = "Dz0"
    Dzn0 = "Dzn0"
    Zd0 = "Zd0"
    ZNd0 = "Nd0"
    Dy5 = "Dy5"
    Dyn5 = "Dyn5"
    Yd5 = "Yd5"
    YNd5 = "Nd5"
    Yz5 = "Yz5"
    YNz5 = "Nz5"
    Yzn5 = "Yzn5"
    YNzn5 = "Nzn5"
    Dd6 = "Dd6"
    Yy6 = "Yy6"
    YNy6 = "Ny6"
    Yyn6 = "Yyn6"
    YNyn6 = "Nyn6"
    Dz6 = "Dz6"
    Dzn6 = "Dzn6"
    Zd6 = "Zd6"
    ZNd6 = "Nd6"
    Dy11 = "Dy11"
    Dyn11 = "Dyn11"
    Yd11 = "Yd11"
    YNd11 = "Nd11"
    Yz11 = "Yz11"
    YNz11 = "Nz11"
    Yzn11 = "Yzn11"
    YNzn11 = "Nzn11"


class TrfPhaseTechnology(enum.IntEnum):
    SINGLE_PH_E = 1
    SINGLE_PH = 2
    THREE_PH = 3


class TrfTapSide(enum.IntEnum):
    HV = 0
    LV = 1


class MetricPrefix(enum.Enum):
    a = "a"
    f = "f"
    p = "p"
    n = "n"
    u = "u"
    m = "m"
    EMPTY = ""
    k = "k"
    M = "M"
    G = "G"
    T = "T"
    P = "P"
    E = "E"


class Currency(enum.Enum):
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    GBP = "GBP"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"
    CNY = "CNY"
    SEK = "SEK"
    MXN = "MXN"
    NZD = "NZD"
    SGD = "SGD"
    HKD = "HKD"
    NOK = "NOK"
    KRW = "KRW"
    TRY = "TRY"
    INR = "INR"
    RUB = "RUB"
    BRL = "BRL"
    ZAR = "ZAR"
    CLP = "CLP"


class ISym(enum.IntEnum):
    SYM = 0
    ASYM = 1


class VoltageSystemType(enum.IntEnum):
    AC = 0
    DC = 1


class UnitSystem(enum.IntEnum):
    METRIC = 0
    ENG_TRANSMISSION = 1
    ENG_INDUSTRY = 2


class Phase(enum.Enum):
    A = "L1"
    B = "L2"
    C = "L3"
    N = "N"


class TerminalVoltageSystemType(enum.IntEnum):
    DC = 0
    AC = 1
    ACBI = 2


class PowerFactoryTypes:
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
        ilenunit: UnitSystem
        clenexp: MetricPrefix  # Lengths
        cspqexp: MetricPrefix  # Loads etc.
        cspqexpgen: MetricPrefix  # Generators etc.
        currency: Currency

    class UnitConversionSetting(DataObject, Protocol):
        filtclass: Sequence[str]
        filtvar: str
        digunit: str
        cdigexp: MetricPrefix
        userunit: str
        cuserexp: MetricPrefix
        ufacA: float  # noqa: N815
        ufacB: float  # noqa: N815

    class DataDir(DataObject, Protocol):
        ...

    class Substation(DataObject, Protocol):
        ...

    class LoadType(DataObject, Protocol):
        loddy: float  # portion of dynamic part of ZIP load model in RMS simulation (100 = 100% dynamic)
        systp: VoltageSystemType
        phtech: LoadPhaseConnectionType

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
        systp: VoltageSystemType
        frnom: float  # nominal frequency the values x and b apply

    class Transformer2WType(DataObject, Protocol):
        vecgrp: VectorGroup
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
        tr2cn_l: Vector
        tr2cn_h: Vector
        nt2ag: float
        nt2ph: TrfPhaseTechnology
        tap_side: TrfTapSide
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
        isclosed: bool
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
        iUsage: NodeType  # noqa: N815
        outserv: bool
        cpSubstat: PowerFactoryTypes.Substation | None  # noqa: N815
        cubics: Sequence[PowerFactoryTypes.StationCubicle]
        systype: TerminalVoltageSystemType

    class StationCubicle(DataObject, Protocol):
        cterm: PowerFactoryTypes.Terminal
        obj_id: PowerFactoryTypes.Line | PowerFactoryTypes.Element | None
        nphase: int
        cPhInfo: str  # noqa: N815

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
        i_ctrl: CtrlMode
        qu_char: QChar
        qsetp: float
        iQorient: QOrient  # noqa: N815
        refbar: PowerFactoryTypes.Terminal
        Srated: float
        ddroop: float
        Qmin: float
        Qmax: float
        udeadblow: float
        udeadbup: float
        cosphi_char: CosphiChar
        pfsetp: float
        pf_recap: PFRecap
        tansetp: float
        usetp: float
        pQPcurve: PowerFactoryTypes.QPCharacteristic  # noqa: N815 # Q(P)-characteristic curve
        p_cub: PowerFactoryTypes.StationCubicle
        u_under: float
        u_over: float
        pf_under: float
        pf_over: float
        p_under: float
        p_over: float
        i_phase: CtrlVoltageRef

    class CompoundModel(DataObject, Protocol):
        ...

    class Element(DataObject, Protocol):
        desc: Sequence[str]
        pf_recap: PFRecap
        bus1: PowerFactoryTypes.StationCubicle | None
        scale0: float

    class GeneratorBase(Element, Protocol):
        ngnum: int
        sgn: float
        cosn: float
        pgini: float
        qgini: float
        cosgini: float
        pf_recap: PFRecap
        Kpf: float
        ddroop: float
        Qfu_min: float
        Qfu_max: float
        udeadblow: float
        udeadbup: float
        outserv: bool
        av_mode: QCtrlTypes
        mode_inp: ModeInpGen
        sgini_a: float
        pgini_a: float
        qgini_a: float
        cosgini_a: float
        pf_recap_a: PFRecap
        scale0_a: float
        c_pstac: PowerFactoryTypes.StationController | None
        c_pmod: PowerFactoryTypes.CompoundModel | None  # Compound Parent Model/Template
        pQPcurve: PowerFactoryTypes.QPCharacteristic | None  # noqa: N815 # Q(P)-characteristic curve
        pf_under: float
        pf_over: float
        p_under: float
        p_over: float
        usetp: float

    class QPCharacteristic(DataObject, Protocol):
        inputmod: Literal[0, 1]

    class Generator(GeneratorBase, Protocol):
        aCategory: GeneratorSystemType  # noqa: N815
        c_psecc: PowerFactoryTypes.SecondaryController | None
        phtech: GeneratorPhaseConnectionType

    class PVSystem(GeneratorBase, Protocol):
        uk: float
        Pcu: float
        phtech: GeneratorPhaseConnectionType

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
        mode_inp: ModeInpLoad
        i_sym: ISym
        u0: float

    class LoadLVP(DataObject, Protocol):
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
        ccosphi: float
        pf_recap: PFRecap

    class LoadLV(LoadBase, LoadLVP, Protocol):
        i_sym: ISym
        lodparts: Sequence[PowerFactoryTypes.LoadLVP]
        phtech: LoadPhaseConnectionType

    class LoadMV(LoadBase, Protocol):
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
        pf_recap: PFRecap
        pfg_recap: PFRecap

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
        bustp: BusType
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
