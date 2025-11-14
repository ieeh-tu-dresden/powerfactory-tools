---
title: 'PowerFactory-Tools: A Python Package to Facilitate the Control of DIgSILENT PowerFactory'
tags:
  - Python
  - Electrical Power System
  - Power System Data Model
  - PowerFactory
  - Automation
authors:
  - name: Sebastian Krahmer
    orcid: 0000-0002-3940-3398
    corresponding: true
    equal-contrib: true
    affiliation: 1
  - name: Sasan Jacob Rasti
    orcid: 0000-0002-1190-051X
    equal-contrib: true
    affiliation: 1
  - name: Laura Fiedler
    orcid: 0000-0002-9425-5324
    equal-contrib: false
    affiliation: 1
  - name: Maximilian Schmidt
    orcid: 0000-0003-2509-8342
    equal-contrib: false
    affiliation: 1

affiliations:
 - name: Institute of Electrical Power Systems and High Voltage Engineering, TUD Dresden University of Technology, Germany
   index: 1
   ror: 042aqky30
date: 16 April 2025
bibliography: paper.bib

---

# Summary

_PowerFactory-Tools_ is a Python package that facilitates the control of PowerFactory, a worldwide used network calculation program. 
The software provides a well-structured and type-safe interface for PowerFactory, thereby simplifying the development, testing and verification of custom Python scripts. 
The package also includes a network exporter that converts PowerFactory data into the open-source _Power System Data Model_ format. 
This enables users to access the nodal admittance matrix of the network, which is restricted in PowerFactory. 
_PowerFactory-Tools_ also provides type hints and autocomplete suggestions, safe unit handling, and a temporary unit conversion to default values. 
The package has been utilised in a variety of research projects. 
This software is a valuable tool for power system engineers and researchers who require network calculations to be automated and streamlined.

# Statement of need

_PowerFactory-Tools_ is a power system affiliated Python package for the control of the commercial network calculation program PowerFactory [@powerfactory].
When it comes to calculations based on use case variations or the need for reproducible control actions, PowerFactory can be called and controlled via user-defined Python scripts.
PowerFactory-Tools eases developing, testing and verification by providing a well-structured and type-safe Python interface for PowerFactory.
This interface is established on top of the PowerFactory-Python-API, but has undergone a process of refinement and augmentation through the incorporation of individually parameterisable functions that prove to be of considerable practical benefit.
A common task in respect to case studies that can be implemented more conveniently with _PowerFactory-Tools_ is, for example, the automated replacement of generators with one's own templates and their parameterisation.

Furthermore, a main functionality is the network exporter from PowerFactory to the open-source _Power System Data Model_ (PSDM) [-@psdm].
In terms of network optimisation, user-defined network reduction or stability analysis, users may require an explicitly accessible nodal admittance matrix (NAM) of the network. 
Since access to this is still restricted for PowerFactory users, exporting the PowerFactory network to a well structured and human readable exchange format is a huge benefit.
Due to this, users can (a) export to _PSDM_ Python objects and build the NAM by your own without changing the programming language or (b) export to _PSDM_-formatted JSON files, then import these files using the programming language of your choice and build the NAM.
It has to mention, that PowerFactory provides a built-in export with DGS, the bidirectional, flexible DIgSILENT data exchange format (ascii, xml, csv, odbc). 
While it is intended to support GIS and SCADA connections, the drawback is that the DGS export is typeless and not Python native. 
Due to this, a significant effort for parsing may occur.

_PowerFactory-Tools_ was used in @Krahmer:2022, @Krahmer:2023, @Krahmer:2024 and @Fiedler:2024 as well as is currently in use in the research project SysZell, ZellSys and digiTechNetz.

# Application Benefits

By implementing a type wrapper for internal PowerFactory element types, users 
receive type hints and autocomplete suggestions to increase the safety and productivity.
Furthermore, _PowerFactory-Tools_ guarantee safe unit handling. 
A temporary unit conversion to default values is automatically performed to have a project setting independent behavior. 
The units are reset when the interface is closed. 
During an active connection to PowerFactory, the following units apply: power in MVA (resp. MW, Mvar), voltage in kV, current in kA and length in km.

A broad range of application examples is provided in the _PowerFactory-Tools_ repository [-@pftools], which encourage beginners.

# Power System Data Model

As previously stated, the _PSDM_ constitutes a secondary open-source toolbox that has been developed in conjunction with the _PowerFactory-Tools_, but not exclusively for them.
It utilizes a hierarchical structure/schema to describe unique entity relations as well as parameter sets. 
_PSDM_ uses the BaseModel class from Pydantic as a technique for defining schema classes.
The PSDM consists of three parts covering different types of information and each part can be stored as a human-readable JSON file:
- Topology: plain network model with nodes, edges and connected devices
- TopologyCase: information about elements that are disconnected, e. g. out-of-service or via open switches
- SteadystateCase: operational case specific information.

A full PSDM-representation of a network can be viewed in the example section of the _PowerFactory-Tools_ repository [-@pftools].
The following code snippet shows how to use the library to export a PowerFactory 2024 network to the _PSDM_ format.

```shell
pip install ieeh-powerfactory-tools
```

```python
import pathlib
from powerfactory_tools.versions.pf2025 import PowerFactoryExporter
from powerfactory_tools.versions.pf2025.interface import ValidPythonVersion

PF_PATH = pathlib.Path("C:/Program Files/DIgSILENT")
PF_SERVICE_PACK = 2 # mandatory
PF_USER_PROFILE = "TODO"  # mandatory, name of the user profile in PF data base
PF_PYTHON_VERSION = ValidPythonVersion.VERSION_3_13
# project name may be also full path "dir_name\project_name"
# (name is choosen related to example PF project in GitHub repository)
PROJECT_NAME = "PowerFactory-Tools"  
# a valid study case name in the choosen PF project
STUDY_CASE_NAME = "Base"  
# directory, the export results will be saved to
EXPORT_PATH = pathlib.Path("export") 

with PowerFactoryExporter(
    powerfactory_path=PF_PATH,
    powerfactory_service_pack=PF_SERVICE_PACK,
    powerfactory_user_profile=PF_USER_PROFILE,
    python_version=PF_PYTHON_VERSION,
    project_name=PROJECT_NAME,
    ) as exporter:
        # Option I: Export to PSDM Python objects
        grids = exporter.pfi.independent_grids(calc_relevant=True)
        for grid in grids:
            grid_name = grid.loc_name
            data = exporter.pfi.compile_powerfactory_data(grid)
            meta = exporter.create_meta_data(data=data, case_name=STUDY_CASE_NAME)

            # Create the three PSDM base classes
            topology = exporter.create_topology(meta=meta, data=data)
            topology_case = exporter.create_topology_case(meta=meta, data=data, 
                topology=topology)
            steadystate_case = exporter.create_steadystate_case(meta=meta, data=data, 
                topology=topology)
            # Now, the PSDM objects can be used by the user ...

        # Option II: Export to PSDM-formatted JSON files
        exporter.export(
            export_path = EXPORT_PATH, 
            study_case_names=[STUDY_CASE_NAME],
        )
```

# Software Dependencies

The software is written in Python and uses the data validation library pydantic [-@pydantic].
In respect to the export functionality, the _PSDM_ [-@psdm] is used as schema for network entity relations.
Ultimately, the responsibility falls upon the user to ensure the accurate compilation of software versions. 
Should any reader require assistance with this topic, they will find an up-to-date list of compatible software available at the repositories readme.
For example, the _PowerFactory-Tools_ version 3.3.0 is related to the _PSDM_ version 2.3.3 and brings built-in support for PowerFactory version 2022, 2024 and 2025.

# Acknowledgements

The tool was developed during work related to the projects STABEEL (project no. 442893506), SysZell (funding code 03EI4074D) and digiTechNetz (funding code 03EI6075A), first funded by the Deutsche Forschungsgemeinschaft (DFG, DOI: 10.13039/501100001659), the latter funded by the German Federal Ministry for Economic Affairs and Climate Action.

# References
