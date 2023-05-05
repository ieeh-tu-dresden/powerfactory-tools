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
    YNy0 = "YNy0"
    Yyn0 = "Yyn0"
    YNyn0 = "YNyn0"
    Dz0 = "Dz0"
    Dzn0 = "Dzn0"
    Zd0 = "Zd0"
    ZNd0 = "ZNd0"
    Dyn1 = "Dyn1"
    Dy5 = "Dy5"
    Dyn5 = "Dyn5"
    Yd5 = "Yd5"
    YNd5 = "YNd5"
    Yz5 = "Yz5"
    YNz5 = "YNz5"
    Yzn5 = "Yzn5"
    YNzn5 = "YNzn5"
    Dd6 = "Dd6"
    Yy6 = "Yy6"
    YNy6 = "YNy6"
    Yyn6 = "Yyn6"
    YNyn6 = "YNyn6"
    Dz6 = "Dz6"
    Dzn6 = "Dzn6"
    Zd6 = "Zd6"
    ZNd6 = "ZNd6"
    Dyn7 = "Dyn7"
    Dy11 = "Dy11"
    Dyn11 = "Dyn11"
    Yd11 = "Yd11"
    YNd11 = "YNd11"
    Yz11 = "Yz11"
    YNz11 = "YNz11"
    Yzn11 = "Yzn11"
    YNzn11 = "YNzn11"


class TrfPhaseTechnology(enum.IntEnum):
    SINGLE_PH_E = 1
    SINGLE_PH = 2
    THREE_PH = 3


class TrfTapSide(enum.IntEnum):
    HV = 0
    LV = 1


class TrfNeutralConnectionType(enum.IntEnum):
    NO = 0
    ABC_N = 1
    HV = 2  # separat at HV side
    LV = 3  # separat at LV side
    HV_LV = 4  # separat at HV and LV side


class TrfNeutralPointState(enum.IntEnum):
    EARTHED = 0
    ISOLATED = 1


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


class HarmonicSourceSystemType(enum.IntEnum):
    SYMMETIRC = 0
    UNSYMMETRIC = 1
    IEC_61000 = 2


class HarmonicLoadModelType(enum.IntEnum):
    IMPEDANCE_TYPE_1 = 0
    CURRENT_SOURCE = 1
    IMPEDANCE_TYPE_2 = 2


class NetworkCalcType(enum.IntEnum):
    AC_SYM_POSITIVE_SEQUENCE = 0
    AC_UNSYM_ABC = 1  # unsym. 3-Phase(abc)


class NetworkExtendedCalcType(enum.IntEnum):
    AC_SYM_POSITIVE_SEQUENCE = 0
    AC_UNSYM_ABC = 1  # unsym. 3-Phase(abc)
    DC = 2


class TemperatureDependencyType(enum.IntEnum):
    DEFAULT_20_DEGREE = 0
    MAX_OPERATION_TEMP = 1
    OPERATION_TEMP = 2
    USER_TEMP = 3


class CalculationType(enum.IntEnum):  # only excerpt
    ALL_CALCULATIONS = 0
    RELIABILITY_MONTE_CARLO = 1
    RELIABILITY_ENUMERATION = 2
    MODAL_ANALYSIS = 5  # Eigenvalues
    HARMONICS = 6
    MONITORING = 7
    TRIGGERED = 8
    FREQUENCY_SWEEP = 9
    VOLTAGE_SAGS = 10
    SHORT_CIRCUIT_SWEEP = 11
    ONLINE_PFM = 12
    CONTINGENCY_ANALYSIS = 13
    OPF_BEFORE_OPTIMISATION = 14
    OPF_AFTER_OPTIMISATION = 15
    SHORT_CIRCUIT = 16
    FFT_CALCULATION = 17
    SHORT_CIRCUIT_EMT = 18
    FLICKER = 19
    QUASI_DYNAMIC_SIMULATION = 29
    PROTECTION = 30
    SENSITIVITY_FACTORS = 31


class CalculationCommand(enum.Enum):  # only excerpt
    LOAD_FLOW = "ComLdf"
    CONTINGENCY_ANALYSIS = "ComContingency"
    FLICKER = "ComFlickermeter"
    SHORT_CIRCUIT_SWEEP = "ComShctrace"
    SHORT_CIRCUIT = "ComShc"
    TIME_DOMAIN_SIMULATION = "ComSim"
    TIME_DOMAIN_SIMULATION_START = "ComInc"
    MODAL_ANALYSIS = "ComMod"
    SENSITIVITY_ANALYSIS = "ComVstab"
    HARMONICS = "ComHldf"
    FREQUENCY_SWEEP = "ComFsweep"


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

        i_crsc: HarmonicLoadModelType
        i_pure: int  # for harmonic load model type IMPEDANCE_TYPE_1; 0 - pure inductive/capacitive; 1 - mixed inductive/capacitive
        Prp: float  # for harmonic load model type IMPEDANCE_TYPE_2; static portion in percent
        pcf: float  # for harmonic load model type IMPEDANCE_TYPE_2; load factor correction in percent

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

        nneutral: bool  # no. of neutral conductors

        systp: VoltageSystemType
        frnom: float  # nominal frequency the values x and b apply

    class LineNType(LineType, Protocol):
        rnline: float  # resistance (Ohm/km) natural neutral components
        rpnline: float  # resistance (Ohm/km) natural neutral-line couple components
        xnline: float  # reactance (Ohm/km) natural neutral components
        xpnline: float  # reactance (Ohm/km) natural neutral-line couple components
        gnline: float  # conductance (µS/km) natural neutral components
        gpnline: float  # conductance (µS/km) natural neutral-line couple components
        bnline: float  # susceptance (µS/km) natural neutral components
        bpnline: float  # susceptance (µS/km) natural neutral-line couple components

    class Transformer2WType(DataObject, Protocol):
        utrn_l: float  # reference voltage LV side
        utrn_h: float  # reference voltage HV side
        pfe: float  # Iron losses
        curmg: float  # no-load current
        pcutr: float  # Cupper losses
        strn: float  # rated power
        uktr: float  # short-circuit voltage in percentage
        r1pu: float
        r0pu: float
        x1pu: float
        x0pu: float
        zx0hl_n: float
        rtox0_n: float

        vecgrp: VectorGroup
        tr2cn_l: Vector  # vector at LV side
        tr2cn_h: Vector  # vector at HV side
        nt2ag: float

        tap_side: TrfTapSide
        ntpmn: int
        ntpmx: int
        nntap0: int
        dutap: float
        phitr: float
        itapch: int
        itapch2: int

        nt2ph: TrfPhaseTechnology

    class Transformer3WType(DataObject, Protocol):
        ...

    class SwitchType(DataObject, Protocol):
        Inom: float
        R_on: float
        X_on: float

    class HarmonicSourceType(DataObject, Protocol):
        i_usym: HarmonicSourceSystemType

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
        ciEnergized: bool  # noqa: N815
        desc: Sequence[str]
        uknom: float
        iUsage: NodeType  # noqa: N815
        outserv: bool
        cStatName: str  # noqa: N815
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

        cneutcon: TrfNeutralConnectionType
        cgnd_h: TrfNeutralPointState
        cgnd_l: TrfNeutralPointState
        cpeter_h: bool
        cpeter_l: bool
        re0tr_h: float
        re0tr_l: float
        xe0tr_h: float
        xe0tr_l: float

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

    class SourceBase(DataObject, Protocol):
        bus1: PowerFactoryTypes.StationCubicle | None
        outserv: bool
        nphase: int
        desc: Sequence[str]
        c_pmod: PowerFactoryTypes.CompoundModel | None  # Compound Parent Model/Template

    class AcCurrentSource(SourceBase, Protocol):
        Ir: float
        isetp: float
        cosini: float
        i_cap: PFRecap
        G1: float
        B1: float
        isetp2: float
        phisetp2: float
        G2: float
        B2: float
        isetp0: float
        phisetp0: float
        G0: float
        B0: float
        phmc: PowerFactoryTypes.HarmonicSourceType | None

    class Result(DataObject, Protocol):
        desc: Sequence[str]
        calTp: CalculationType  # noqa: N815

        def AddVariable(  # noqa: N802
            self,
            element: PowerFactoryTypes.DataObject,
            varname: str,
            /,
        ) -> int:
            ...

        def Clear(self) -> int:  # noqa: N802  # Always 0 and can be ignored
            ...

        def FindColumn(  # noqa: N802
            self,
            obj: PowerFactoryTypes.DataObject,
            varName: str,  # noqa: N803
            startCol: int,  # noqa: N803
            /,
        ) -> int:
            ...

        def GetNumberOfColumns(self) -> None:  # noqa: N802
            ...

        def GetNumberOfRows(self) -> None:  # noqa: N802
            ...

        def GetValue(  # noqa: N802  # Returns a value from a result object for row iX of curve col.
            self,
            iX: int,  # noqa: N803
            col: int,
            /,
        ) -> int:
            ...

        def Load(self) -> None:  # noqa: N802
            ...

        def Release(self) -> None:  # noqa: N802
            ...

    class CommandBase(DataObject, Protocol):
        def Execute(self) -> int:  # noqa: N802
            ...

    class CommandLoadFlow(CommandBase, Protocol):
        iopt_net: NetworkExtendedCalcType
        iPST_at: bool  # noqa: N815  # automatic step control of phase shifting transformers
        iopt_plim: bool  # apply active power limits
        iopt_at: bool  # automatic step control of transformers
        iopt_asht: bool  # automatic step control of compensators/filters
        iopt_lim: bool  # apply reactive power limits
        iopt_tem: TemperatureDependencyType
        temperature: float
        iopt_pq: bool  # apply voltage dependecy of loads
        iopt_fls: bool  # load scaling at defined feeders

        i_power: int  # load flow method; 0 - NewtonRaphson (current eq.); 1 - Newton Raphson (power eq.)[default]

        scLoadFac: float  # noqa: N815  # load scaling factor in percentage
        scGenFac: float  # noqa: N815  # generator scaling factor in percentage
        scMotFac: float  # noqa: N815  # motor scaling factor in percentage
        zoneScale: int  # noqa: N815  # zone scaling; 0 - apply for all loads; 1 - apply only for scalable loads

    class CommandHarmonicCalculation(CommandBase, Protocol):
        iopt_sweep: int
        iopt_allfrq: int
        iopt_flicker: bool
        iopt_SkV: bool  # noqa: N815
        iopt_pseq: bool
        iopt_net: NetworkCalcType
        frnom: float
        fshow: float
        ifshow: float
        p_resvar: PowerFactoryTypes.Result

        errmax: float
        errinc: float
        ninc: float
        iopt_thd: int

    class CommandFrequencySweep(CommandBase, Protocol):
        iopt_net: NetworkCalcType
        ildfinit: bool  # load flow initialisation
        fstart: float
        fstep: float
        fstop: float
        i_adapt: bool  # automatic step size adaption

    class Script(Protocol):
        def SetExternalObject(  # noqa: N802
            self,
            name: str,
            value: PowerFactoryTypes.DataObject,
            /,
        ) -> int:
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

        def GetActiveStudyCase(self) -> PowerFactoryTypes.StudyCase:  # noqa: N802
            ...

        def GetProjectFolder(  # noqa: N802
            self,
            name: str,
            /,
        ) -> PowerFactoryTypes.DataObject:
            ...

        def GetFromStudyCase(  # noqa: N802
            self,
            className: str,  # noqa: N803
            /,
        ) -> PowerFactoryTypes.DataObject:
            ...

        def PostCommand(  # noqa: N802
            self,
            command: Literal["exit"],
            /,
        ) -> None:
            ...

        def ExecuteCmd(  # noqa: N802
            self,
            command: str,
            /,
        ) -> None:
            ...

        def EchoOff(self) -> None:  # noqa: N802
            ...

        def EchoOn(self) -> None:  # noqa: N802
            ...

        def GetCalcRelevantObjects(  # noqa: N802
            self,
            nameFilter: str,  # noqa: N803
            includeOutOfService: int,  # noqa: N803
            topoElementsOnly: int,  # noqa: N803
            bAcSchemes: int,  # noqa: N803
            /,
        ) -> set:
            ...

    class PowerFactoryModule(Protocol):
        ExitError: tuple[type[Exception], ...]

        def GetApplicationExt(  # noqa: N802
            self,
            username: str | None = None,
            password: str | None = None,
            commandLineArguments: str | None = None,  # noqa: N803
            /,
        ) -> PowerFactoryTypes.Application:
            ...
