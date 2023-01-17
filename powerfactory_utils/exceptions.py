# -*- coding: utf-8 -*-
# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from powerfactory_utils.powerfactory_types import PowerFactoryTypes as PFTypes


class Exceptions:
    class LoadPFModuleError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not load PowerFactory Module.")

    class ProjectActivationError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not activate project.")

    class ProjectDeactivationError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not deactivate project.")

    class CouldNotCloseAppError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not close application.")

    class GridActivationError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not activate grid.")

    class GridDeactivationError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not deactivate grid.")

    class ScenarioActivationError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not activate scenario.")

    class ScenarioDeactivationError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not deactivate scenario.")

    class StudyCaseActivationError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not activate case study.")

    class StudyCaseDeactivationError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not deactivate case study.")

    class DataDirAccessError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not access data dir.")

    class InvalidPathError(FileNotFoundError):
        def __init__(self) -> None:
            super().__init__("Invalid Path.")

    class ScenarioSwitchError(RuntimeError):
        def __init__(self, scen: str) -> None:
            super().__init__(f"Could not switch scenerio. Scenario {scen} does not exist.")

    class StudyCaseSwitchError(RuntimeError):
        def __init__(self, sc: str) -> None:
            super().__init__(f"Could not switch study case. Study Case {sc} does not exist.")

    class TopologyExportError(RuntimeError):
        pass

    class TopologyCaseExportError(RuntimeError):
        pass

    class SteadystateCaseExportError(RuntimeError):
        pass

    class SteadystateCaseNotValidError(ValueError):
        def __init__(self) -> None:
            super().__init__("Steadystate case does not match specified topology.")

    class ExportError(FileNotFoundError):
        def __init__(self) -> None:
            super().__init__("Export failed.")

    class ProjectAccessError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not access project.")

    class ProjectSettingsAccessError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not access project settings.")

    class UnitSettingsAccessError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not access unit settings.")

    class SettingsAccessError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("Could not access settings.")

    class ElementDeletionError(RuntimeError):
        def __init__(self, element: PFTypes.DataObject) -> None:
            super().__init__(f"Could not delete element {element}.")
