# -*- coding: utf-8 -*-


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


class InvalidPathError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid Path.")


class ScenarioSwitchError(Exception):
    def __init__(self, scen: str) -> None:
        super().__init__(f"Could not switch scenerio. Scenario {scen} does not exist.")


class StudyCaseSwitchError(Exception):
    def __init__(self, sc: str) -> None:
        super().__init__(f"Could not switch study case. Study Case {sc} does not exist.")


class InvalidSteadystateCaseError(Exception):
    pass


class TopologyExportError(Exception):
    pass


class TopologyCaseExportError(Exception):
    pass


class SteadystateCaseExportError(Exception):
    pass


class ExportError(Exception):
    pass


class ProjectAccessError(Exception):
    def __init__(self) -> None:
        super().__init__("Could not access project.")


class ProjectSettingsAccessError(Exception):
    def __init__(self) -> None:
        super().__init__("Could not access project settings.")


class UnitSettingsAccessError(Exception):
    def __init__(self) -> None:
        super().__init__("Could not access unit settings.")


class SettingsAccessError(Exception):
    def __init__(self) -> None:
        super().__init__("Could not access settings.")
