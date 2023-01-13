from __future__ import annotations

from typing import Literal
from typing import Optional
from typing import Protocol
from typing import Sequence
from typing import Union

ModeInpLoad = Literal["DEF", "PQ", "PC", "IC", "SC", "QC", "IP", "SP", "SQ"]
ModeInpGen = Literal["DEF", "PQ", "PC", "SC", "QC", "SP", "SQ"]
ModeInpMV = Literal["PC", "SC", "EC"]
IOptInp = Literal[0, 1, 2, 3]
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
    fold_id: Optional[DataObject]

    def GetContents(self, filter: str, recursive: bool = False) -> list[DataObject]:
        ...

    def CreateObject(self, class_name: str, name: Optional[Union[str, int]], /) -> Optional[DataObject]:
        ...

    def Delete(self) -> int:
        ...


class GridDiagram(DataObject, Protocol):
    ...


class Graph(DataObject, Protocol):
    sSymName: str
    pDataObj: Optional[DataObject]
    rCenterX: float
    rCenterY: float
    rSizeX: float
    rSizeY: float
    iRot: int
    iLevel: int
    iCol: int
    iCollapsed: bool
    iIndLS: int
    iVis: bool


class Project(DataObject, Protocol):
    pPrjSettings: Optional[ProjectSettings]

    def Deactivate(self) -> bool:
        ...


class Scenario(DataObject, Protocol):
    def Activate(self) -> bool:
        ...

    def Deactivate(self) -> bool:
        ...


class StudyCase(DataObject, Protocol):
    def Activate(self) -> bool:
        ...

    def Deactivate(self) -> bool:
        ...


class ProjectSettings(DataObject, Protocol):
    extDataDir: DataDir
    ilenunit: Literal[0, 1, 2]
    clenexp: MetricPrefix  # Lengths
    cspqexp: MetricPrefix  # Loads etc.
    cspqexpgen: MetricPrefix  # Generators etc.
    currency: Currency


class UnitConversionSetting(DataObject, Protocol):
    filtclass: list[str]
    filtvar: str
    digunit: str
    cdigexp: MetricPrefix
    userunit: str
    cuserexp: MetricPrefix
    ufacA: float
    ufacB: float


class DataDir(DataObject, Protocol):
    ...


DefaultPFReturnData = Union[float, str, DataObject, list[float], list[str], list[DataObject], None]


class Substation(DataObject, Protocol):
    ...


class LoadType(DataObject, Protocol):
    loddy: float  # portion of dynamic part of ZIP load model in RMS simulation (100 = 100% dynamic)
    systp: bool  # 0:AC; 1:DC
    phtech: PhTechLoad  # phase connection: [0, 2, 3, 4, 5, 7, 8, 9] cfg. schema.load.PhaseConnectionType

    aP: float  # a-portion of the active power in relation to ZIP load model
    bP: float  # b-portion of the active power in relation to ZIP load model
    cP: float  # c-portion of the active power in relation to ZIP load model
    kpu0: float  # exponent of the a-portion of the active power in relation to ZIP load model
    kpu1: float  # exponent of the b-portion of the active power in relation to ZIP load model
    kpu: float  # exponent of the c-portion of the active power in relation to ZIP load model

    aQ: float  # a-portion of the reactive power in relation to ZIP load model
    bQ: float  # b-portion of the reactive power in relation to ZIP load model
    cQ: float  # c-portion of the reactive power in relation to ZIP load model
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
    vecgrp: TrfVectorGroup
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
    tr2cn_l: TrfVector
    tr2cn_h: TrfVector
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
    bus1: Optional[StationCubicle]
    bus2: Optional[StationCubicle]
    typ_id: Optional[SwitchType]
    cpSubstat: Optional[Substation]
    isclosed: bool  # 0:open; 1:closed
    desc: list[str]


class Grid(DataObject, Protocol):
    def Activate(self) -> bool:
        ...

    def Deactivate(self) -> bool:
        ...


class LineBase(DataObject, Protocol):
    cDisplayName: str
    desc: list[str]
    outserv: bool


class Terminal(DataObject, Protocol):
    cDisplayName: str
    desc: list[str]
    uknom: float
    iUsage: Literal[0, 1, 2]  # 0:bus bar; 1:junction node; 2:internal node
    outserv: bool
    cpSubstat: Optional[Substation]
    cubics: list[StationCubicle]


class StationCubicle(DataObject, Protocol):
    cterm: Terminal
    obj_id: Optional[Union[Line, Element]]


class Transformer2W(LineBase, Protocol):
    buslv: Optional[StationCubicle]
    bushv: Optional[StationCubicle]
    ntnum: int
    typ_id: Optional[Transformer2WType]
    nntap: int


class Transformer3W(LineBase, Protocol):
    buslv: Optional[StationCubicle]
    busmv: Optional[StationCubicle]
    bushv: Optional[StationCubicle]
    nt3nm: int
    typ_id: Optional[Transformer3WType]
    n3tapl: int
    n3tapm: int
    n3taph: int


class ControllerBase(DataObject, Protocol):
    c_pmod: Optional[CompoundModel]


class SecondaryController(ControllerBase, Protocol):
    ...


class StationController(ControllerBase, Protocol):
    i_ctrl: Literal[0, 1, 2, 3]  # 0:Voltage Control; 1:Reactive Power Control; 2:Cosphi Control; 3:Tanphi Control
    qu_char: Literal[0, 1, 2]  # 0:const. Q; 1:Q(U); 2: Q(P)
    qsetp: float
    iQorient: Literal[0, 1]  # 0:+Q; 1:-Q
    refbar: Terminal
    Srated: float
    ddroop: float
    Qmin: float
    Qmax: float
    udeadblow: float
    udeadbup: float
    cosphi_char: Literal[0, 1, 2]  # 0:const. Cosphi; 1:Cosphi(P); 2:Cosphi(U)
    pfsetp: float
    pf_recap: PFRecap
    tansetp: float


class CompoundModel(DataObject, Protocol):
    ...


class Element(DataObject, Protocol):
    desc: list[str]
    pf_recap: PFRecap  # 0:over excited; 1:under excited
    bus1: Optional[StationCubicle]
    scale0: float


class GeneratorBase(Element, Protocol):
    ngnum: int
    sgn: float
    cosn: float
    pgini: float
    qgini: float
    cosgini: float
    pf_recap: PFRecap  # 0:over excited; 1:under excited
    Kpf: float
    ddroop: float
    Qfu_min: float
    Qfu_max: float
    udeadblow: float
    udeadbup: float
    outserv: bool
    av_mode: QCtrlTypes
    mode_inp: ModeInpGen
    phtech: PhTechGen
    sgini_a: float
    pgini_a: float
    qgini_a: float
    cosgini_a: float
    pf_recap_a: PFRecap  # 0:over excited; 1:under excited
    scale0_a: float
    c_pstac: Optional[StationController]
    c_pmod: Optional[CompoundModel]  # Compound Parent Model/Template


class Generator(GeneratorBase, Protocol):
    cCategory: GenSystemType
    c_psecc: Optional[SecondaryController]


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
    typ_id: Optional[LoadType]


class Load(LoadBase, Protocol):
    mode_inp: ModeInpLoad  # DEF:Default; PQ:P,Q; PC:P,cosphi; IC:I,cosphi; SC:S,cosphi; QC:Q,cosphi; IP:I,P; SP:S,P; SQ:S,Q
    i_sym: bool  # 0:symmetrical; 1:asymmetrical
    u0: float


class LoadLVP(DataObject, Protocol):
    iopt_inp: IOptInp  # 0:S,cosphi; 1:P,cosphi,2:U,I,cosphi; 3:E,cosphi
    elini: float
    cplinia: float
    slini: float
    plini: float
    qlini: float
    ilini: float
    coslini: float
    ulini: float
    pnight: float
    cSav: float
    ccosphi: float


class LoadLV(LoadBase, LoadLVP, Protocol):
    i_sym: bool  # 0:symmetrical; 1:asymmetrical
    lodparts: Sequence[LoadLVP]


class LoadMV(LoadBase, Protocol):
    mode_inp: ModeInpMV
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
    pfg_recap: PFRecap  # 0:over excited; 1:under excited


class Switch(DataObject, Protocol):
    fold_id: StationCubicle
    isclosed: bool  # 0:open; 1:closed


class Fuse(DataObject, Protocol):
    ...


class Line(LineBase, Protocol):
    bus1: Optional[StationCubicle]
    bus2: Optional[StationCubicle]
    nlnum: int  # no. of parallel lines
    dline: float  # line length (km)
    fline: float  # installation factor
    inAir: bool  # 0:soil; 1:air
    Inom_a: float  # nominal current (actual)
    typ_id: Optional[LineType]


class ExternalGrid(DataObject, Protocol):
    bustp: BusType
    bus1: Optional[StationCubicle]
    desc: list[str]
    usetp: float  # in p.u.
    pgini: float  # in MW
    qgini: float  # in Mvar
    phiini: float  # in deg
    snss: float  # in MVA
    snssmin: float  # in MVA
    outserv: bool


class Script(Protocol):
    def SetExternalObject(self, name: str, value: DataObject) -> int:
        ...

    def Execute(self) -> int:
        ...


class Application(Protocol):
    def ActivateProject(self, name: str) -> int:
        ...

    def GetActiveProject(self) -> Project:
        ...

    def GetProjectFolder(self, name: str) -> DataObject:
        ...


class PowerFactoryModule(Protocol):
    ExitError: tuple[type[Exception], ...]

    def GetApplicationExt(
        self, username: Optional[str] = None, password: Optional[str] = None, commandLineArguments: Optional[str] = None
    ) -> Application:
        ...
