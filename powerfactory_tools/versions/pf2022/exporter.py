# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2024.
# :license: BSD 3-Clause

from __future__ import annotations

import logging
import multiprocessing
import pathlib
import typing as t

import loguru
import pydantic
from psdm.meta import Meta
from psdm.meta import SignConvention
from psdm.steadystate_case.case import Case as SteadystateCase
from psdm.topology.topology import Topology
from psdm.topology_case.case import Case as TopologyCase

from powerfactory_tools.__version__ import VERSION
from powerfactory_tools.base.exporter.exporter import PowerFactoryExporter as PowerFactoryExporterBase
from powerfactory_tools.base.interface import DEFAULT_POWERFACTORY_PATH
from powerfactory_tools.versions.pf2022.interface import DEFAULT_PYTHON_VERSION
from powerfactory_tools.versions.pf2022.interface import PYTHON_VERSIONS
from powerfactory_tools.versions.pf2022.interface import PowerFactoryInterface

if t.TYPE_CHECKING:
    import pathlib
    from collections.abc import Sequence

    from powerfactory_tools.versions.pf2022.data import PowerFactoryData
    from powerfactory_tools.versions.pf2022.types import PowerFactoryTypes as PFTypes

    ElementBase = PFTypes.GeneratorBase | PFTypes.LoadBase3Ph | PFTypes.ExternalGrid


class PowerFactoryExporterProcess(multiprocessing.Process):
    def __init__(  # noqa: PLR0913
        self,
        *,
        export_path: pathlib.Path,
        project_name: str,
        powerfactory_user_profile: str = "",
        powerfactory_path: pathlib.Path = DEFAULT_POWERFACTORY_PATH,
        powerfactory_service_pack: int | None = None,
        python_version: PYTHON_VERSIONS = DEFAULT_PYTHON_VERSION,
        logging_level: int = logging.DEBUG,
        log_file_path: pathlib.Path | None = None,
        topology_name: str | None = None,
        topology_case_name: str | None = None,
        steadystate_case_name: str | None = None,
        study_case_names: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.export_path = export_path
        self.project_name = project_name
        self.powerfactory_user_profile = powerfactory_user_profile
        self.powerfactory_path = powerfactory_path
        self.powerfactory_service_pack = powerfactory_service_pack
        self.python_version = python_version
        self.logging_level = logging_level
        self.log_file_path = log_file_path
        self.topology_name = topology_name
        self.topology_case_name = topology_case_name
        self.steadystate_case_name = steadystate_case_name
        self.study_case_names = study_case_names

    def run(self) -> None:
        pfe = PowerFactoryExporter(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            logging_level=self.logging_level,
            log_file_path=self.log_file_path,
        )
        pfe.export(
            export_path=self.export_path,
            topology_name=self.topology_name,
            topology_case_name=self.topology_case_name,
            steadystate_case_name=self.steadystate_case_name,
            study_case_names=self.study_case_names,
        )


@pydantic.dataclasses.dataclass
class PowerFactoryExporter(PowerFactoryExporterBase):
    python_version: PYTHON_VERSIONS = DEFAULT_PYTHON_VERSION

    def __post_init__(self) -> None:
        self.pfi = PowerFactoryInterface(
            project_name=self.project_name,
            powerfactory_user_profile=self.powerfactory_user_profile,
            powerfactory_path=self.powerfactory_path,
            powerfactory_service_pack=self.powerfactory_service_pack,
            python_version=self.python_version,
            logging_level=self.logging_level,
            log_file_path=self.log_file_path,
        )

    @staticmethod
    def create_meta_data(
        *,
        data: PowerFactoryData,
        case_name: str,
    ) -> Meta:
        loguru.logger.debug("Creating meta data...")
        grid_name = data.grid_name.replace(" ", "-")
        project_name = data.project_name.replace(" ", "-")
        date = data.date

        return Meta(
            case=case_name,
            date=date,
            grid=grid_name,
            project=project_name,
            sign_convention=SignConvention.PASSIVE,
            creator=f"powerfactory-tools @ version {VERSION}",
        )

    def create_topology(
        self,
        *,
        meta: Meta,
        data: PowerFactoryData,
    ) -> Topology:
        loguru.logger.debug("Creating topology...")
        external_grids = self.create_external_grids(
            data.external_grids,
            grid_name=data.grid_name,
        )
        nodes = self.create_nodes(data.terminals, grid_name=data.grid_name)
        branches = self.create_branches(
            lines=data.lines,
            couplers=data.couplers,
            fuses=data.bfuses,
            grid_name=data.grid_name,
        )
        loads = self.create_loads(
            consumers=data.loads,
            consumers_lv=data.loads_lv,
            consumers_mv=data.loads_mv,
            generators=data.generators,
            pv_systems=data.pv_systems,
            grid_name=data.grid_name,
        )
        transformers = self.create_transformers(
            data.transformers_2w,
            grid_name=data.grid_name,
        )

        return Topology(
            meta=meta,
            nodes=nodes,
            branches=branches,
            loads=loads,
            transformers=transformers,
            external_grids=external_grids,
        )

    def create_topology_case(
        self,
        *,
        meta: Meta,
        data: PowerFactoryData,
    ) -> TopologyCase:
        loguru.logger.debug("Creating topology case...")
        switch_states = self.create_switch_states(data.switches, grid_name=data.grid_name)
        coupler_states = self.create_coupler_states(data.couplers, grid_name=data.grid_name)
        bfuse_states = self.create_bfuse_states(data.bfuses, grid_name=data.grid_name)
        efuse_states = self.create_efuse_states(data.efuses, grid_name=data.grid_name)
        elements: Sequence[ElementBase] = self.pfi.list_from_sequences(
            data.loads,
            data.loads_lv,
            data.loads_mv,
            data.generators,
            data.pv_systems,
            data.external_grids,
        )
        node_power_on_states = self.create_node_power_on_states(data.terminals, grid_name=data.grid_name)
        line_power_on_states = self.create_element_power_on_states(data.lines, grid_name=data.grid_name)
        transformer_2w_power_on_states = self.create_element_power_on_states(
            data.transformers_2w,
            grid_name=data.grid_name,
        )
        element_power_on_states = self.create_element_power_on_states(elements, grid_name=data.grid_name)
        power_on_states = self.pfi.list_from_sequences(
            switch_states,
            coupler_states,
            bfuse_states,
            efuse_states,
            node_power_on_states,
            line_power_on_states,
            transformer_2w_power_on_states,
            element_power_on_states,
        )
        power_on_states = self.merge_power_on_states(power_on_states)

        return TopologyCase(meta=meta, elements=power_on_states)

    def create_steadystate_case(
        self,
        *,
        meta: Meta,
        data: PowerFactoryData,
    ) -> SteadystateCase:
        loguru.logger.info("Creating steadystate case...")
        loads = self.create_loads_ssc(
            consumers=data.loads,
            consumers_lv=data.loads_lv,
            consumers_mv=data.loads_mv,
            generators=data.generators,
            pv_systems=data.pv_systems,
            grid_name=data.grid_name,
        )
        transformers = self.create_transformers_ssc(
            data.transformers_2w,
            grid_name=data.grid_name,
        )
        external_grids = self.create_external_grid_ssc(
            data.external_grids,
            grid_name=data.grid_name,
        )

        return SteadystateCase(
            meta=meta,
            loads=loads,
            transformers=transformers,
            external_grids=external_grids,
        )


def export_powerfactory_data(  # noqa: PLR0913
    *,
    export_path: pathlib.Path,
    project_name: str,
    powerfactory_user_profile: str = "",
    powerfactory_path: pathlib.Path = DEFAULT_POWERFACTORY_PATH,
    powerfactory_service_pack: int | None = None,
    python_version: PYTHON_VERSIONS = DEFAULT_PYTHON_VERSION,
    logging_level: int = logging.DEBUG,
    log_file_path: pathlib.Path | None = None,
    topology_name: str | None = None,
    topology_case_name: str | None = None,
    steadystate_case_name: str | None = None,
    study_case_names: list[str] | None = None,
) -> None:
    """Export powerfactory data to json files using PowerFactoryExporter running in process.

    A grid given in DIgSILENT PowerFactory is exported to three json files with given schema.
    The whole grid data is separated into topology (raw assets), topology_case (binary switching info and out of service
    info) and steadystate_case (operation points).
    When the code execution is complete, the process is terminated and the connection to PowerFactory is closed.

    Arguments:
        export_path {pathlib.Path} -- the directory where the exported json files are saved
        project_name {str} -- project name in PowerFactory to which the grid belongs
        powerfactory_user_profile {str} -- user profile for login in PowerFactory (default: {""})
        powerfactory_path {pathlib.Path} -- installation directory of PowerFactory (default: {POWERFACTORY_PATH})
        powerfactory_service_pack {int} -- the service pack version of PowerFactory (default: {None})
        python_version {PYTHON_VERSIONS} -- the version of Python to be used for PowerFactory (default: {DEFAULT_PYTHON_VERSION})
        logging_level {int} -- flag for the level of logging criticality (default: {DEBUG})
        log_file_path {pathlib.Path} -- the file path of an external log file (default: {None})
        topology_name {str} -- the chosen file name for 'topology' data (default: {None})
        topology_case_name {str} -- the chosen file name for related 'topology_case' data (default: {None})
        steadystate_case_name {str} -- the chosen file name for related 'steadystate_case' data (default: {None})
        study_case_names {list[str]} -- a list of study cases to export (default: {None})

    Returns:
        None
    """

    process = PowerFactoryExporterProcess(
        project_name=project_name,
        export_path=export_path,
        powerfactory_user_profile=powerfactory_user_profile,
        powerfactory_path=powerfactory_path,
        powerfactory_service_pack=powerfactory_service_pack,
        python_version=python_version,
        logging_level=logging_level,
        log_file_path=log_file_path,
        topology_name=topology_name,
        topology_case_name=topology_case_name,
        steadystate_case_name=steadystate_case_name,
        study_case_names=study_case_names,
    )
    process.start()
    process.join()
