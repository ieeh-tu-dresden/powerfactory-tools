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


class PFClassId(enum.Enum):
    AREA = "ElmArea"
    COMPOSITE_GRID_ELEMENT = "ElmFolder"
    COUPLER = "ElmCoup"
    CUBICLE = "StaCubic"
    CURRENT_SOURCE_AC = "ElmIac"
    EXTERNAL_GRID = "ElmXNet"
    DATETIME = "SetTime"
    FOLDER = "IntFolder"
    FUSE = "RelFuse"
    FUSE_TYPE = "TypFuse"
    GENERATOR = "ElmGenstat"
    GRID = "ElmNet"
    GRID_GRAPHIC = "IntGrfnet"
    LINE = "ElmLne"
    LINE_TYPE = "TypLne"
    LOAD = "ElmLod"
    LOAD_LV = "ElmLodLv"
    LOAD_LV_PART = "ElmLodlvp"
    LOAD_MV = "ElmLodMv"
    LOAD_TYPE_GENERAL = "TypLod"
    LOAD_TYPE_HARMONIC = "TypHmccur"
    PROJECT_FOLDER = "IntPrjfolder"
    PROJECT_SETTINGS = "SetPrj"
    PVSYSTEM = "ElmPvsys"
    REFERENCE = "IntRef"
    RESULT = "ElmRes"
    SCENARIO = "IntScenario"
    SETTINGS_FOLDER = "SetFold"
    SETTINGS_FOLDER_UNITS = "IntUnit"
    STATION_CONTROLLER = "ElmStactrl"
    STUDY_CASE = "IntCase"
    SWITCH = "StaSwitch"
    TEMPLATE = "IntTemplate"
    TERMINAL = "ElmTerm"
    TRANSFORMER_2W = "ElmTr2"
    TRANSFORMER_2W_TYPE = "TypTr2"
    TRANSFORMER_3W = "ElmTr3"
    TRANSFORMER_3W_TYPE = "TypTr3"
    UNIT_VARIABLE = "SetVariable"
    VARIABLE_MONITOR = "IntMon"  # Variable monitor definition
    VARIANT = "IntScheme"
    VARIANT_CONFIG = "IntAcscheme"
    VARIANT_STAGE = "IntSstage"
    ZONE = "ElmZone"


class FolderType(enum.Enum):
    CB_RATINGS = "cbrat"
    CIM_MODEL = "cim"
    CHARACTERISTICS = "chars"
    COMMON_MODE_FAILURES = "common"
    DEMAND_TRANSFERS = "demand"
    DIAGRAMS = "dia"
    EQUIPMENT_TYPE_LIBRARY = "equip"
    FAULTS = "fault"
    GENERIC = "gen"
    GENERATOR_COST_CURVES = "cstgen"
    GENERATOR_EFFICIENCY_CURVES = "effgen"
    LIBRARY = "lib"
    MVAR_LIMIT_CURVES = "mvar"
    NETWORK_DATA = "netdat"
    NETWORK_MODEL = "netmod"
    OPERATIONAL_LIBRARY = "oplib"
    OPERATION_SCENARIOS = "scen"
    OUTAGES = "outage"
    QP_CURVES = "qpc"
    PROBABILISTIC_ASSESSMENT = "rnd"
    RUNNING_ARRANGEMENTS = "ra"
    REMEDIAL_ACTION_SCHEMES = "ras"
    SCRIPTS = "script"
    STATION_WARE = "sw"
    STUDY_CASES = "study"
    TABLE_REPORTS = "report"
    TARIFFS = "tariff"
    TEMPLATES = "templ"
    THERMAL_RATINGS = "therm"
    USER_DEFINED_MODELS = "blk"
    VARIATIONS = "scheme"
    V_CONTROL_CURVES = "ucc"


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


class CosPhiChar(enum.IntEnum):
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


class TerminalPhaseConnectionType(enum.IntEnum):
    THREE_PH = 0
    THREE_PH_N = 1
    BI = 2
    BI_N = 3
    TWO_PH = 4
    TWO_PH_N = 5
    ONE_PH = 6
    ONE_PH_N = 7
    N = 8


class GeneratorPhaseConnectionType(enum.IntEnum):
    THREE_PH_D = 0
    THREE_PH_PH_E = 1
    ONE_PH_PH_E = 2
    ONE_PH_PH_N = 3
    ONE_PH_PH_PH = 4


class LoadLVPhaseConnectionType(enum.IntEnum):
    THREE_PH_D = 0
    THREE_PH_PH_E = 2
    THREE_PH_YN = 3
    TWO_PH_PH_E = 4
    TWO_PH_YN = 5
    ONE_PH_PH_PH = 7
    ONE_PH_PH_N = 8
    ONE_PH_PH_E = 9


class LoadPhaseConnectionType(enum.Enum):
    THREE_PH_D = "3PH-'D'"
    THREE_PH_PH_E = "3PH PH-E"
    THREE_PH_YN = "3PH-'YN'"
    TWO_PH_PH_E = "2PH PH-E"
    TWO_PH_YN = "2PH-'YN'"
    ONE_PH_PH_PH = "1PH PH-PH"
    ONE_PH_PH_N = "1PH PH-N"
    ONE_PH_PH_E = "1PH PH-E"


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
    YNyn5 = "YNyn5"
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
    HV = 2  # separate at HV side
    LV = 3  # separate at LV side
    HV_LV = 4  # separate at HV and LV side


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


class FuseCharacteristicType(enum.Enum):
    NS = 0
    NH = 1
    HH = 2


class UnitSystem(enum.IntEnum):
    METRIC = 0
    ENG_TRANSMISSION = 1
    ENG_INDUSTRY = 2


class Phase3PH(enum.Enum):
    A = "L1"
    B = "L2"
    C = "L3"
    N = "N"


class Phase2PH(enum.Enum):
    A = "DP1"
    B = "DP2"
    N = "N"


class Phase1PH(enum.Enum):
    A = "SP"
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


class TimeSimulationType(enum.Enum):
    RMS = "rms"
    EMT = "ins"


class TimeSimulationNetworkCalcType(enum.Enum):
    AC_SYM_POSITIVE_SEQUENCE = "sym"
    AC_UNSYM_ABC = "rst"  # unsym. 3-Phase(abc)


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
    CONTINGENCY_ANALYSIS = "ComContingency"
    FLICKER = "ComFlickermeter"
    FREQUENCY_SWEEP = "ComFsweep"
    GRAPHIC_LAYOUT_TOOL = "ComSgllayout"
    HARMONICS = "ComHldf"
    LOAD_FLOW = "ComLdf"
    MODAL_ANALYSIS = "ComMod"
    RESULT_EXPORT = "ComRes"
    SENSITIVITY_ANALYSIS = "ComVstab"
    SHORT_CIRCUIT = "ComShc"
    SHORT_CIRCUIT_SWEEP = "ComShctrace"
    TIME_DOMAIN_SIMULATION = "ComSim"
    TIME_DOMAIN_SIMULATION_START = "ComInc"


class SelectionTarget(enum.IntEnum):  # only excerpt
    CONTINGENCY_ANALYSIS = 0
    SHORT_CIRCUIT = 1
    OUTPUTS = 2
    GENERAL = 5
    SGL_LAYOUT = 23


class SelectionType(enum.IntEnum):
    K_NEIGHBORHOOD = 0
    GRIDS = 1
    FEEDERS = 2
    INTERCHANGE_NEIGHBORHOOD = 3


class ResultExportMode(enum.IntEnum):
    INTERNAL_OUTPUT_WINDOW = 0
    WINDOWS_CLIPBOARD = 1
    MEASUREMENT_DATA_FILE = 2  # ElmFile
    COMTRADE = 3
    TEXT_FILE = 4
    PSSPLT_VERSION_2 = 5
    CSV = 6
    DATABSE = 7


class ResultExportVariableSelection(enum.IntEnum):
    ALL = 0
    SELECTED = 1


class ResultExportColumnHeadingElement(enum.IntEnum):
    NONE = 0
    NAME = 1
    SHORT_PATH_AND_NAME = 2
    PATH_AND_NAME = 3
    FOREIGN_KEY = 4


class ResultExportColumnHeadingVariable(enum.IntEnum):
    NONE = 0
    NAME = 1
    SHORT_DESCRIPTION = 2
    FULL_DESCRIPTION = 3


class ResultExportIntervalFilter(enum.IntEnum):
    NONE = 0
    UNDERSAMPLING = 1
    SYMMETRIC_MEAN_VALUE = 2
    FLOATING_SYMMETRIC_MEAN_VALUE = 3


class ResultExportNumberFormat(enum.IntEnum):
    DECIMAL = 0
    SCIENTIFIC = 1


class PowerFactoryTypes:
    class DataObject(Protocol):
        loc_name: str
        fold_id: PowerFactoryTypes.DataObject | None

        def AddCopy(  # noqa: N802
            self,
            object_to_copy: PowerFactoryTypes.DataObject | Sequence[PowerFactoryTypes.DataObject],
            concat_name_part: str | int = "",
            /,
        ) -> PowerFactoryTypes.DataObject | None:
            ...

        def CreateObject(  # noqa: N802
            self,
            class_name: str,
            name: str | int | None,
            /,
        ) -> PowerFactoryTypes.DataObject | None:
            ...

        def CopyData(self, source: PowerFactoryTypes.DataObject) -> int:  # noqa: N802
            ...

        def Delete(self) -> int:  # noqa: N802
            ...

        def GetClassName(self) -> str:  # noqa: N802
            ...

        def GetContents(  # noqa: N802
            self,
            name: str,
            recursive: bool = False,  # noqa: FBT001, FBT002
            /,
        ) -> Sequence[PowerFactoryTypes.DataObject]:
            ...

        def GetParent(self) -> PowerFactoryTypes.DataObject | None:  # noqa: N802
            ...

        def IsCalcRelevant(self) -> int:  # noqa: N802
            ...

        def IsEarthed(self) -> int:  # noqa: N802
            ...

        def IsEnergized(self) -> int:  # noqa: N802
            ...

        def IsObjectActive(  # noqa: N802  # Check if an object is active for specific time.
            self,
            time: int,  # Time in seconds since 01.01.1970 00:00:00
            /,
        ) -> int:
            ...

    class DataDir(DataObject, Protocol):
        ...

    class GridDiagram(DataObject, Protocol):  # PFClassId.GRID_GRAPHIC
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

    class Scenario(DataObject, Protocol):  # PFClassId.SCENARIO
        def Activate(self) -> bool:  # noqa: N802
            ...

        def Deactivate(self) -> bool:  # noqa: N802
            ...

    class StudyCase(DataObject, Protocol):  # PFClassId.STUDY_CASE
        iStudyTime: int  # noqa: N815

        def Activate(self) -> bool:  # noqa: N802
            ...

        def ApplyNetworkState(  # noqa: N802
            self,
            other: PowerFactoryTypes.DataObject,  # the other study case to copy from: grids, scenarios and network variations configuration
        ) -> Literal[0, 1, 2, 3, 4, 5]:
            ...

        def ApplyStudyTime(  # noqa: N802
            self,
            other: PowerFactoryTypes.DataObject,  # the other study case to copy from: study time
        ) -> Literal[0, 1, 2, 3, 4]:
            ...

        def Consolidate(self) -> bool:  # noqa: N802
            ...

        def Deactivate(self) -> bool:  # noqa: N802
            ...

        def SetStudyTime(  # noqa: N802
            self,
            date_time: int,  # Seconds since 01.01.1970 00:00:00.
        ) -> None:
            ...

    class GridVariant(DataObject, Protocol):  # PFClassId.VARIANT
        def Activate(self) -> bool:  # noqa: N802
            ...

        def Deactivate(self) -> bool:  # noqa: N802
            ...

        def NewStage(  # noqa: N802
            self,
            name: str,
            activation_time: int,  # Activation time of the new expansion stage in seconds since 01.01.1970 00:00:00
            activate: int,  # 1 - Activate (should be dafault); 0 - do not activate
            /,
        ) -> bool:
            ...

    class GridVariantStage(DataObject, Protocol):  # PFClassId.VARIANT_STAGE
        tAcTime: str  # noqa: N815
        iExclude: int  # noqa: N815

        def Activate(self) -> bool:  # noqa: N802
            ...

        def GetVariation(self) -> PowerFactoryTypes.GridVariant:  # noqa: N802
            ...

    class ProjectSettings(DataObject, Protocol):  # PFClassId.PROJECT_SETTINGS
        extDataDir: str  # noqa: N815
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

    class Substation(DataObject, Protocol):
        ...

    class LoadType(DataObject, Protocol):  # PFClassId.LOAD_TYPE_GENERAL
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

    class LineType(DataObject, Protocol):  # PFClassId.LINE_TYPE
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

        nlnph: float  # no. of phase conducters
        nneutral: float  # no. of neutral conductors

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

    class Transformer2WType(DataObject, Protocol):  # PFClassId.TRANSFORMER_2W_TYPE
        utrn_l: float  # reference voltage LV side
        utrn_h: float  # reference voltage HV side
        pfe: float  # Iron losses
        curmg: float  # no-load current
        pcutr: float  # Cupper losses
        strn: float  # rated power
        uktr: float  # short-circuit voltage in percentage (pos. seq.)
        uk0tr: float  # short-circuit voltage in percentage (zero. seq.)
        ur0tr: float  # real part of uk0tr
        r1pu: float
        r0pu: float
        x1pu: float
        x0pu: float
        zx0hl_n: float  # Zero Sequence Magnetising Impedance: Mag. Impedance / uk0
        rtox0_n: float  # Zero Sequence Magnetising R/X ratio: Mag. R/X
        itrdr: float  # Distribution of Leakage Resistances (p.u.): r, Pos.Seq. HV-Side
        itrdr_lv: float  # Distribution of Leakage Resistances (p.u.): r, Pos.Seq. LV-Side
        itrdl: float  # Distribution of Leakage Reactances (p.u.): x, Pos.Seq. HV-Side
        itrdl_lv: float  # Distribution of Leakage Reactances (p.u.): x, Pos.Seq. LV-Side
        zx0hl_h: float  # Distribution of Zero Sequ. Leakage-Impedances: z, Zero Seq. HV-Side
        zx0hl_l: float  # Distribution of Zero Sequ. Leakage-Impedances: z, Zero Seq. LV-Side
        x0tor0: float  # Zero Sequence Impedance: Ratio X0/R0

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

    class Transformer3WType(DataObject, Protocol):  # PFClassId.TRANSFORMER_3W_TYPE
        ...

    class SwitchType(DataObject, Protocol):  # PFClassId.SWITCH
        Inom: float
        R_on: float
        X_on: float

    class HarmonicSourceType(DataObject, Protocol):  # PFClassId.LOAD_TYPE_HARMONIC
        i_usym: HarmonicSourceSystemType

    class Coupler(DataObject, Protocol):  # PFClassId.COUPLER
        bus1: PowerFactoryTypes.StationCubicle | None
        bus2: PowerFactoryTypes.StationCubicle | None
        typ_id: PowerFactoryTypes.SwitchType | None
        cpSubstat: PowerFactoryTypes.Substation | None  # noqa: N815
        isclosed: bool
        desc: Sequence[str]

    class Grid(DataObject, Protocol):  # PFClassId.GRID
        def Activate(self) -> bool:  # noqa: N802
            ...

        def Deactivate(self) -> bool:  # noqa: N802
            ...

    class LineBase(DataObject, Protocol):
        cDisplayName: str  # noqa: N815
        desc: Sequence[str]
        outserv: bool

    class Terminal(DataObject, Protocol):  # PFClassId.TERMINAL
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
        phtech: TerminalPhaseConnectionType

    class StationCubicle(DataObject, Protocol):  # PFClassId.CUBICLE
        cterm: PowerFactoryTypes.Terminal
        obj_id: PowerFactoryTypes.Line | PowerFactoryTypes.Element | None
        nphase: int
        cPhInfo: str  # noqa: N815

    class Transformer2W(LineBase, Protocol):  # PFClassId.TRANSFORMER_2W
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

    class Transformer3W(LineBase, Protocol):  # PFClassId.TRANSFORMER_3W
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
        cosphi_char: CosPhiChar
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
        phtech: GeneratorPhaseConnectionType

    class QPCharacteristic(DataObject, Protocol):
        inputmod: bool

    class Generator(GeneratorBase, Protocol):  # PFClassId.GENERATOR
        aCategory: GeneratorSystemType  # noqa: N815
        c_psecc: PowerFactoryTypes.SecondaryController | None

    class PVSystem(GeneratorBase, Protocol):  # PFClassId.PVSYSTEM
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

    class Load(LoadBase, Protocol):  # PFClassId.LOAD
        mode_inp: ModeInpLoad
        i_sym: ISym
        u0: float
        phtech: LoadPhaseConnectionType

    class LoadLVP(DataObject, Protocol):  # PFClassId.LOAD_LV_PART
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
        pf_recap: PFRecap
        phtech: LoadLVPhaseConnectionType

    class LoadLV(LoadBase, LoadLVP, Protocol):  # PFClassId.LOAD_LV
        i_sym: ISym
        lodparts: Sequence[PowerFactoryTypes.LoadLVP]
        phtech: LoadLVPhaseConnectionType

    class LoadMV(LoadBase, Protocol):  # PFClassId.LOAD_MV
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
        phtech: LoadPhaseConnectionType

    class Switch(DataObject, Protocol):  # PFClassId.SWITCH
        fold_id: PowerFactoryTypes.StationCubicle
        isclosed: bool  # 0:open; 1:closed

    class Line(LineBase, Protocol):  # PFClassId.LINE
        bus1: PowerFactoryTypes.StationCubicle | None
        bus2: PowerFactoryTypes.StationCubicle | None
        nlnum: int  # no. of parallel lines
        dline: float  # line length (km)
        fline: float  # installation factor
        inAir: bool  # noqa: N815 # 0:soil; 1:air
        Inom_a: float  # nominal current (actual)
        typ_id: PowerFactoryTypes.LineType | None

    class FuseType(DataObject, Protocol):  # PFClassId.FUSE_TYPE
        urat: float  # rated voltage
        irat: float  # rated current
        frq: float  # nominal frequency
        itype: FuseCharacteristicType

    class Fuse(DataObject, Protocol):  # PFClassId.FUSE
        desc: Sequence[str]
        typ_id: PowerFactoryTypes.FuseType | None
        on_off: bool  # closed = 1; open = 0
        outserv: bool
        bus1: PowerFactoryTypes.StationCubicle | None
        bus2: PowerFactoryTypes.StationCubicle | None

    class BFuse(Fuse, Protocol):
        ...

    class EFuse(Fuse, Protocol):
        fold_id: PowerFactoryTypes.StationCubicle
        cn_bus: PowerFactoryTypes.Terminal
        cbranch: PowerFactoryTypes.LineBase | PowerFactoryTypes.Element | PowerFactoryTypes.Fuse
        bus1: None
        bus2: None

    class ExternalGrid(DataObject, Protocol):  # PFClassId.EXTERNAL_GRID
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

    class AcCurrentSource(SourceBase, Protocol):  # PFClassId.CURRENT_SOURCE_AC
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

    class Template(DataObject, Protocol):
        ...

    class Events(DataObject, Protocol):
        ...

    class Selection(DataObject, Protocol):  # SetSelect
        iused: SelectionTarget
        iusedSub: SelectionType  # noqa: N815

        def AddRef(  # noqa: N802
            self,
            element: PowerFactoryTypes.DataObject | list[PowerFactoryTypes.DataObject],
            /,
        ) -> None:
            ...

        def All(self) -> Sequence[PowerFactoryTypes.DataObject]:  # noqa: N802
            ...

        def GetAll(  # noqa: N802
            self,
            class_name: str,
            /,
        ) -> Sequence[PowerFactoryTypes.DataObject]:
            ...

        def AllElm(self) -> Sequence[PowerFactoryTypes.Element]:  # noqa: N802
            ...

        def Clear(self) -> None:  # noqa: N802
            ...

    class VariableMonitor(DataObject, Protocol):
        obj_id: PowerFactoryTypes.DataObject

        def AddVar(  # noqa: N802
            self,
            var_name: str,
            /,
        ) -> None:
            ...

        def AddVars(  # noqa: N802
            self,
            var_filter: str,  # e.g.: "e:*"
            /,
        ) -> None:
            ...

        def ClearVars(self) -> None:  # noqa: N802
            ...

        def GetVar(  # noqa: N802
            self,
            row: int,  # the row number of the attribute in the defined list of the variable monitor
            /,
        ) -> str:  # the variable name in line row
            ...

        def NVars(self) -> int:  # noqa: N802
            """Returns the number of selected variables.

            More exact, the number of lines in the variable selection text on the second page
            of the IntMon dialogue, which usually contains one variable name per line.
            """
            ...

        def RemoveVar(  # noqa: N802
            self,
            var_name: str,
            /,
        ) -> bool:
            ...

        def PrintAllValues(self) -> None:  # noqa: N802
            ...

        def PrintVal(self) -> None:  # noqa: N802
            ...

    class Result(DataObject, Protocol):  # PFClassId.RESULT
        desc: Sequence[str]
        calTp: CalculationType  # noqa: N815

        def AddVariable(  # noqa: N802
            self,
            element: PowerFactoryTypes.DataObject,
            var_name: str,
            /,
        ) -> int:
            ...

        def Clear(self) -> int:  # noqa: N802  # Always 0 and can be ignored
            ...

        def FindColumn(  # noqa: N802
            self,
            obj: PowerFactoryTypes.DataObject,
            var_name: str,
            start_col: int,
            /,
        ) -> int:
            ...

        def FinishWriting(self) -> None:  # noqa: N802
            """Closes the result object after writing."""
            ...

        def Flush(self) -> int:  # noqa: N802
            """This function is required in scripts which perform both file writing and reading operations.

            All data must be written to the disk before attempting to read the file.
            'Flush' copies all data buffered in memory to the disk.
            After calling 'Flush'all data is available to be read from the file.
            """

        def GetNumberOfColumns(self) -> None:  # noqa: N802
            ...

        def GetNumberOfRows(self) -> None:  # noqa: N802
            ...

        def GetUnit(self, column: int, /) -> str:  # noqa: N802
            ...

        def GetValue(  # noqa: N802
            self,
            row: int,
            col: int,
            /,
        ) -> tuple[int, float]:  # first: error code; second: retrieved value
            """Returns a value from a result object for row of curve col."""
            ...

        def GetVariable(self, column: int, /) -> str:  # noqa: N802
            ...

        def InitialiseWriting(self) -> int:  # noqa: N802
            """Opens the result object for writing."""
            ...  # Always 0 and can be ignored

        def Load(self) -> None:  # noqa: N802
            """Loads the data of a result object (ElmRes) in memory for reading."""
            ...

        def Release(self) -> None:  # noqa: N802
            """Releases the data loaded to memory."""
            ...

        def Write(  # noqa: N802
            self,
            default_value: float = float("nan"),  # optional default value
            /,
        ) -> int:
            """Writes the current results (specified by VariableMonitor) to the result object."""
            ...

    class CommandBase(DataObject, Protocol):
        def Execute(self) -> int:  # noqa: N802
            ...

    class CommandLoadFlow(CommandBase, Protocol):  # CalculationCommand.LOAD_FLOW
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

        def IsAC(self) -> int:  # noqa: N802
            ...

        def IsDC(self) -> int:  # noqa: N802
            ...

        def IsBalanced(self) -> int:  # noqa: N802
            ...

    class CommandHarmonicCalculation(CommandBase, Protocol):  # CalculationCommand.HARMONIC_LOADFLOW
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

    class CommandFrequencySweep(CommandBase, Protocol):  # CalculationCommand.FREQUENCY_SWEEP
        iopt_net: NetworkCalcType
        ildfinit: bool  # load flow initialisation
        fstart: float
        fstep: float
        fstop: float
        i_adapt: bool  # automatic step size adaption

    class CommandSglLayout(CommandBase, Protocol):  # CalculationCommand.GRAPHIC_LAYOUT_TOOL
        iAction: int  # noqa: N815
        orthoType: int  # noqa: N815
        insertionMode: int  # noqa: N815
        nodeDispersion: int  # noqa: N815
        neighborhoodSize: int  # noqa: N815
        neighborStartElems: PowerFactoryTypes.Selection  # noqa: N815

    class CommandTimeSimulationStart(CommandBase, Protocol):  # CalculationCommand.TIME_DOMAIN_SIMULATION_START
        iopt_sim: TimeSimulationType
        iopt_net: TimeSimulationNetworkCalcType
        iopt_show: int
        iopt_adapt: int  # automatic step size adaption
        iReuseLdf: int  # re-use load flow results # noqa: N815
        p_event: PowerFactoryTypes.Events  # collection of events to be used
        p_resvar: PowerFactoryTypes.Result  # result object to be used for savings
        c_butldf: PowerFactoryTypes.CommandLoadFlow  # related load flow object if used

        dtgrd: float  # step size electro-mechanical
        dtemt: float  # step size electro-magnetic
        tstart: float  # start time related to 0 seconds

    class CommandTimeSimulation(CommandBase, Protocol):  # CalculationCommand.TIME_DOMAIN_SIMULATION
        tstop: float  # final simulation time
        cominc: PowerFactoryTypes.CommandTimeSimulationStart

        def GetSimulationTime(self) -> int:  # noqa: N802
            ...

    class CommandResultExport(CommandBase, Protocol):  # CalculationCommand.RESULT_EXPORT
        f_name: str  # only for specific ResultExportMode (2, 3, 4, 5, 6)
        ciopt_head: ResultExportColumnHeadingVariable
        col_Sep: str  # for csv: colunm separator  # noqa: N815
        dec_Sep: str  # for csv: decimal separator  # noqa: N815
        filtered: ResultExportIntervalFilter
        # from: float  # only when using specific interval: start time in seconds
        iopt_csel: ResultExportVariableSelection
        iopt_exp: ResultExportMode
        iopt_locn: ResultExportColumnHeadingElement
        iopt_rscl: bool  # move time scale
        iopt_sep: bool  # True if system separator should be used
        iopt_tsel: bool  # use specific interval
        iopt_vars: Literal[0, 1, 2]
        nsteps: int  # only when filtered is not 0
        numberFormat: ResultExportNumberFormat  # noqa: N815
        numberPrecisionFixed: int  # number of digits after decimal point  # noqa: N815
        pResult: PowerFactoryTypes.Result  # noqa: N815
        scl_start: float  # only when iopt_rscl is True: new start time in seconds
        to: float  # only when using specific interval: end time in seconds

        def ExportFullRange(self) -> None:  # noqa: N802
            ...

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

    class ProjectFolder(DataObject, Protocol):  # PFClassId.FOLDER
        desc: Sequence[str]
        iopt_typ: FolderType

        def GetProjectFolderType(self) -> str:  # noqa: N802
            ...

        def IsProjectFolderType(self, folder_type: str) -> int:  # noqa: N802
            ...

    class Application(Protocol):
        def ActivateProject(self, name: str) -> int:  # noqa: N802
            ...

        def GetActiveProject(self) -> PowerFactoryTypes.Project | None:  # noqa: N802
            ...

        def GetActiveScenario(self) -> PowerFactoryTypes.Scenario | None:  # noqa: N802
            ...

        def GetActiveStages(  # noqa: N802
            self,
            varied_folder: PowerFactoryTypes.DataObject,
            /,
        ) -> Sequence[PowerFactoryTypes.GridVariantStage]:
            ...

        def GetActiveNetworkVariations(self) -> Sequence[PowerFactoryTypes.GridVariant]:  # noqa: N802
            ...

        def GetActiveStudyCase(self) -> PowerFactoryTypes.StudyCase | None:  # noqa: N802
            ...

        def GetProjectFolder(  # noqa: N802
            self,
            name: str,
            /,
        ) -> PowerFactoryTypes.DataObject:
            ...

        def GetFromStudyCase(  # noqa: N802
            self,
            class_name: str,
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
            name_filter: str,
            include_out_of_service: int,
            topo_elements_only: int = 0,
            b_ac_schemes: int = 0,
            /,
        ) -> Sequence[PowerFactoryTypes.DataObject]:
            ...

    class PowerFactoryModule(Protocol):
        ExitError: tuple[type[Exception], ...]

        def GetApplicationExt(  # noqa: N802
            self,
            username: str | None = None,
            password: str | None = None,
            command_line_arguments: str | None = None,
            /,
        ) -> PowerFactoryTypes.Application:
            ...


ValidPFPrimitive = PowerFactoryTypes.DataObject | str | bool | int | float | None
ValidPFValue = ValidPFPrimitive | list[ValidPFPrimitive] | dict[str, ValidPFPrimitive]
