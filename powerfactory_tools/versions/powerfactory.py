# :author: Sasan Jacob Rasti <sasan_jacob.rasti@tu-dresden.de>
# :author: Sebastian Krahmer <sebastian.krahmer@tu-dresden.de>
# :copyright: Copyright (c) Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, 2022-2023.
# :license: BSD 3-Clause

from __future__ import annotations

import pathlib
import typing as t


class PfData(t.TypedDict):
    types: str
    exporter: str
    interface: str
    pf_version: str
    pf_path: pathlib.Path
    python_version: str


PF_VERSIONS: dict[str, PfData] = {
    "2022SP2": {
        "types": "powerfactory_tools.versions.pf2022_sp2.types",
        "exporter": "powerfactory_tools.versions.2022_sp2.exporter",
        "interface": "powerfactory_tools.versions.2022_sp2.interface",
        "pf_version": "2022 SP2",
        "pf_path": pathlib.Path("C:/Program Files/DIgSILENT"),
        "python_version": "3.10",
    },
}

LATEST = "2022SP2"
DEFAULT_PF_VERSION = PF_VERSIONS[LATEST]["pf_version"]
DEFAULT_PF_PATH = PF_VERSIONS[LATEST]["pf_path"]
DEFAULT_PYTHON_VERSION = PF_VERSIONS[LATEST]["python_version"]
SUPPORTED_VERSIONS = list(PF_VERSIONS.keys())
