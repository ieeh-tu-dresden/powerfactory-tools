# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2023.
# :license: BSD 3-Clause

from __future__ import annotations

import dataclasses
import datetime
import multiprocessing
import pathlib
import typing

import pydantic
from data_io import to_json
from loguru import logger

from powerfactory_tools.interface import PowerFactoryInterface
from powerfactory_tools.powerfactory_types import CalculationCommand as PFCalcCommand
from powerfactory_tools.powerfactory_types import NetworkExtendedCalcType

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType

    from powerfactory_tools.powerfactory_types import PowerFactoryTypes as PFTypes


POWERFACTORY_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
POWERFACTORY_VERSION = "2022 SP2"
PYTHON_VERSION = "3.10"


@dataclasses.dataclass
class PowerFactoryData:
    name: str
    date: datetime.date
    project: str
    external_grids: Sequence[PFTypes.ExternalGrid]
    terminals: Sequence[PFTypes.Terminal]
    lines: Sequence[PFTypes.Line]
    transformers_2w: Sequence[PFTypes.Transformer2W]
    transformers_3w: Sequence[PFTypes.Transformer3W]
    loads: Sequence[PFTypes.Load]
    loads_lv: Sequence[PFTypes.LoadLV]
    loads_mv: Sequence[PFTypes.LoadMV]
    generators: Sequence[PFTypes.Generator]
    pv_systems: Sequence[PFTypes.PVSystem]
    couplers: Sequence[PFTypes.Coupler]
    switches: Sequence[PFTypes.Switch]
    fuses: Sequence[PFTypes.Fuse]
    ac_current_sources: Sequence[PFTypes.AcCurrentSource]


class PowerFactoryControllerProcess(multiprocessing.Process):
    def __init__(
        self,
        *,
        export_path: pathlib.Path,
        project_name: str,
        grid_name: str,
        export_data_name: str = "",
        powerfactory_user_profile: str = "",
        powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
        powerfactory_version: str = POWERFACTORY_VERSION,
        python_version: str = PYTHON_VERSION,
    ) -> None:
        super().__init__()
        self.export_path = export_path
        self.project_name = project_name
        self.grid_name = grid_name
        self.export_data_name = export_data_name
        self.powerfactory_user_profile = powerfactory_user_profile
        self.powerfactory_path = powerfactory_path
        self.powerfactory_version = powerfactory_version
        self.python_version = python_version

    def run(self) -> None:
        pfc = PowerFactoryController(
            project_name=self.project_name,
            grid_name=self.grid_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
            python_version=self.python_version,
        )
        pfc.apply_control_1(
            export_path=self.export_path,
            export_data_name=self.export_data_name,
        )


@pydantic.dataclasses.dataclass
class PowerFactoryController:
    project_name: str
    grid_name: str
    powerfactory_user_profile: str = ""
    powerfactory_user_password: str = ""
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH
    powerfactory_version: str = POWERFACTORY_VERSION
    powerfactory_ini_name: str = ""
    python_version: str = PYTHON_VERSION

    def __post_init__(self) -> None:
        self.pfi = PowerFactoryInterface(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_user_password=self.powerfactory_user_password,
            powerfactory_path=self.powerfactory_path,
            powerfactory_version=self.powerfactory_version,
            powerfactory_ini_name=self.powerfactory_ini_name,
            python_version=self.python_version,
        )

    def __enter__(self) -> PowerFactoryController:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self.pfi.close()

    def apply_control_1(
        self,
        export_path: pathlib.Path,
        export_data_name: str = "",
    ) -> None:
        """Execute user definded control action 1.

        This is an example for addressing different types of PowerFactory elements and run a load flow calculation.

        Arguments:
            export_path {pathlib.Path} -- the directory where the exported json files are saved
            export_data_name {str} -- name of optional exported data

        """

        logger.debug("Apply control action 1 @ {project_name}...", project_name=self.project_name)

        data = self.compile_powerfactory_data()

        scenario = self.pfi.app.GetActiveScenario()  # noqa: F841

        # All nodes of active study case which are in service
        terms = self.pfi.app.GetCalcRelevantObjects("*.ElmTerm", 0)
        terminals = [typing.cast("PFTypes.Terminal", term) for term in terms]

        # All nodes in grid {grid_name}, also these that are out of service
        terminals_2 = data.terminals  # noqa: F841

        # Select only terminals with nominal voltage of xx kV
        voltage_threshold = 110
        terminals_sel = []  # selected terminals
        for term in terminals:
            # nominal voltage
            u_n = term.uknom
            if u_n == voltage_threshold:
                terminals_sel.append(term)

        # Select the harmonic loads for the analysis
        loads = self.pfi.loads(name="Load*")

        # change magnitude harmonics
        for load in loads:
            load.plini = 2  # active power in MW

        result_data = {}

        ## init load flow - sym or unsym
        # Typing is not necessary, but recommended so that the IDE code can give some code completion proposals
        ldf = typing.cast(
            "PFTypes.CommandLoadFlow",
            self.pfi.app.GetFromStudyCase(PFCalcCommand.LOAD_FLOW.value),
        )
        ldf.iopt_net = NetworkExtendedCalcType.AC_UNSYM_ABC.value
        error: int = ldf.Execute()
        if error != 0:
            logger.error("Load flow execution failed.")

        ## store results
        self.export_data(
            data=result_data,
            export_data_name=export_data_name,
            export_path=export_path,
        )

    def switch_study_case(self, sc: str) -> None:
        study_case = self.pfi.study_case(name=sc)
        if study_case is not None:
            self.pfi.activate_study_case(study_case)
        else:
            msg = f"Study case {sc} does not exist."
            raise RuntimeError(msg)

    def switch_scenario(self, scen: str) -> None:
        scenario = self.pfi.scenario(name=scen)
        if scenario is not None:
            self.pfi.activate_scenario(scenario)
        else:
            msg = f"Scenario {scen} does not exist."
            raise RuntimeError(msg)

    def compile_powerfactory_data(self) -> PowerFactoryData:
        logger.debug("Compiling data from PowerFactory...")
        if self.grid_name == "*":
            name = self.project_name
        else:
            grids = self.pfi.grids()
            try:
                grid = [e for e in grids if e.loc_name == self.grid_name][0]
                name = grid.loc_name
            except IndexError as e:
                msg = f"Grid {self.grid_name} does not exist."
                raise RuntimeError(msg) from e

        project = self.pfi.project.loc_name
        date = datetime.datetime.now().astimezone().date()  # noqa: DTZ005

        return PowerFactoryData(
            name=name,
            date=date,
            project=project,
            external_grids=self.pfi.external_grids(grid=self.grid_name),
            terminals=self.pfi.terminals(grid=self.grid_name),
            lines=self.pfi.lines(grid=self.grid_name),
            transformers_2w=self.pfi.transformers_2w(grid=self.grid_name),
            transformers_3w=self.pfi.transformers_3w(grid=self.grid_name),
            loads=self.pfi.loads(grid=self.grid_name),
            loads_lv=self.pfi.loads_lv(grid=self.grid_name),
            loads_mv=self.pfi.loads_mv(grid=self.grid_name),
            generators=self.pfi.generators(grid=self.grid_name),
            pv_systems=self.pfi.pv_systems(grid=self.grid_name),
            couplers=self.pfi.couplers(grid=self.grid_name),
            switches=self.pfi.switches(grid=self.grid_name),
            fuses=self.pfi.fuses(grid=self.grid_name),
            ac_current_sources=self.pfi.ac_current_sources(grid=self.grid_name),
        )

    def export_data(
        self,
        data: dict,
        export_data_name: str | None,
        export_path: pathlib.Path,
    ) -> None:
        """Export data to json file.

        Arguments:
            data {dict} -- data to export
            data_name {str | None} -- the chosen file name for data
            export_path {pathlib.Path} -- the directory where the exported json file is saved
        """
        timestamp = datetime.datetime.now().astimezone()  # noqa: DTZ005
        timestamp_string = timestamp.isoformat(sep="T", timespec="seconds").replace(":", "")
        if export_data_name is None:
            filename = f"{self.project_name}_{timestamp_string}.json"
        else:
            filename = f"{export_data_name}.json"

        file_path = export_path / filename
        try:
            file_path.resolve()
        except OSError as e:
            msg = f"File path {file_path} is not a valid path."
            raise FileNotFoundError(msg) from e

        to_json(data=data, file_path=file_path)


def apply_control_1(  # noqa: PLR0913
    export_path: pathlib.Path,
    project_name: str,
    grid_name: str,
    export_data_name: str = "",
    powerfactory_user_profile: str = "",
    powerfactory_user_password: str = "",
    powerfactory_path: pathlib.Path = POWERFACTORY_PATH,
    powerfactory_version: str = POWERFACTORY_VERSION,
    powerfactory_ini_name: str = "",
    python_version: str = PYTHON_VERSION,
) -> None:
    """Execute user definded control action 1.

    TODO Description of control action.

    Arguments:
        export_path {pathlib.Path} -- the directory where the exported json files are saved
        project_name {str} -- project name in PowerFactory to which the grid belongs
        grid_name {str} -- name of the grid to exported
        export_data_name {str} -- name of optional exported data
        powerfactory_user_profile {str} -- user profile for login in PowerFactory
        powerfactory_path {pathlib.Path} -- installation directory of PowerFactory (hard-coded in interface.py)
        powerfactory_version {str} -- version number of PowerFactory (hard-coded in interface.py)


    Returns:
        None
    """

    process = PowerFactoryControllerProcess(
        project_name=project_name,
        export_path=export_path,
        grid_name=grid_name,
        export_data_name=export_data_name,
        powerfactory_user_profile=powerfactory_user_profile,
        powerfactory_user_password=powerfactory_user_password,
        powerfactory_path=powerfactory_path,
        powerfactory_version=powerfactory_version,
        powerfactory_ini_name=powerfactory_ini_name,
        python_version=python_version,
    )
    process.start()
    process.join()


if __name__ == "__main__":
    import pathlib

    PROJECT_NAME = "pf_project_dir\project_name"  # may be also full path "dir_name\project_name"  # noqa: W605
    GRID_NAME = "grid_name"
    EXPORT_PATH = pathlib.Path("export")
    PF_USER_PROFILE = ""  # specification may be necessary
    PF_INI_NAME = ""  # optional specification of ini file name to switch to full version (e.g. PowerFactoryFull for file PowerFactoryFull.ini)
    PYTHON_VERSION = "3.10"

    with PowerFactoryController(
        project_name=PROJECT_NAME,
        grid_name=GRID_NAME,
        powerfactory_user_profile=PF_USER_PROFILE,
        powerfactory_ini_name=PF_INI_NAME,
        python_version=PYTHON_VERSION,
    ) as controller:
        # run function "apply_control_1"
        controller.apply_control_1(EXPORT_PATH, export_data_name=f"{GRID_NAME}-sequence_voltages_currents")
