# IEEH PowerFactory Tools

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

A toolbox for Python based control of DIgSILENT PowerFactory.

- [IEEH PowerFactory Tools](#ieeh-powerfactory-tools)
  - [Field of Application](#application)
  - [PowerFactory Interface](#interface)
  - [General Remarks on Export](#remarks)
  - [Tutorials](#tutorials)
  - [Installation](#installation)
  - [Compatibility](#compatibility)
  - [Development](#development)
  - [Acknowledgement](#acknowledgement)
  - [Attribution](#attribution)

## <div id="application" /> Field of Application

This application is intended to use for an external usage ('engine mode') of the power flow calculation program [DIgSILENT PowerFactory](https://www.digsilent.de/de/powerfactory.html).
Therefore, the Python-PowerFactory-API, provided by the company, is utilized.

The following functionalities are provided:

- **Interface**: collection of comfort functions for the work with the PowerFactory API
- **Exporter**: export of calculation relevant grid data from a PowerFactory project to the [IEEH Power System Data Model (PSDM)](https://github.com/ieeh-tu-dresden/power-system-data-model)
- **Importer**: import from external grid data into the PowerFactory environment [intended in future release]

**Important**: As the set of different elements, data types and attributes can differ between the various main versions (e.g. `2022`) of PowerFactory, all functionalities are set up individual for main versions.


## <div id="interface" /> PowerFactory Interface
The toolbox builds up on the [PowerFactoryInterface](./powerfactory_tools/versions/pf2022/interface.py), that provides comfort functions to:
- connect to PowerFactory
- create and alter PowerFactory elements ("physical" elements, "organizational" elements, commands, etc.)
- collect PowerFactory elements of specific types
- execute PowerFactory commands
- ...

## <div id="remarks" /> General Remarks

Please find below some important general remarks and assumptions to consider for the application.

### General

A connection to PowerFactory is established via [PowerFactoryInterface](./powerfactory_tools/versions/pf2022/interface.py).
After this initialization, a **temporary unit conversion to default values is automatically performed** to have a project setting independent behavior. The units are reset when the interface is closed.
During an active connection, the following units apply:

- power in MW
- voltage in kV
- current in kA
- length in km  

### Exporter

The [PowerFactoryExporter](./powerfactory_tools/versions/pf2022/exporter/exporter.py) connects to PowerFactory via [PowerFactoryInterface](./powerfactory_tools/versions/pf2022/interface.py).

- The grid export follows the rules of usage recommended by [PSDM](https://github.com/ieeh-tu-dresden/power-system-data-model#-general-remarks):
  - The passive sign convention is used for all types of loads (consumer as well as producer).
  - The `Rated Power` is always defined positive (absolute value).
- By default, all assests of all active grids within the selected study case are to be exported, see [example readme](./examples/README.md).
  - Assets can be excluded by writing `do_not_export` in the first line of the description field.

- The following type of elements are supported:
  - `ElmLne` - a symmetrical overhead line / cable  
  - `ElmTerm` - a network terminal / bus
  - `ElmCoup` - a bus-bus switch (e.g. a circuit breaker in a detailed switching gear)
  - `ElmTr2` - a symmetrical 2-winding transformers
  - `ElmTr3` - a symmetrical 3-winding transformers (in future releases)
  - `ElmLod` - a general load (asym. / sym.)
  - `ElmLodmv` - a medium voltage load
  - `ElmLodlv` - a low voltage load
  - `ElmLodlvp` - a partial low voltage load
  - `ElmPvsys` - a PV system (generator)
  - `ElmGenstat` - a static generator
  - `ElmXnet` - an external grid representation
  - `RelFuse` - a fuse (bus-bus or bus-load)

- Remarks on export of `loads`:
  - The default load model of general loads (`ElmLod`) is of type `const. impedance`.
  - The default load model of medium-voltage loads (`ElmLodmv`) is of type `const. power`.
  - The default load model of low-voltage loads (`ElmLodlv`, `ElmLodlvp`) is of type `const. current`.
  - Be aware that the reference voltage of the load model must not match the nominal voltage of the terminal the load is connected to.
  - By default, the power factor direction of the rated power is set to "not defined", see docs at [LoadPower - as_rated_power()](./powerfactory_tools/versions/pf2022/exporter/load_power.py).
  - Connected consumer loads with an active and reactive power of zero leads to a RatedPower of `NaN`. Consider to exclude them for export.

- Remarks on export of `transformer`:
  - The impedances of all winding objects are referred to the high voltage side of the transformer.
  - The impedance of transformer earthing is an absolute natural value.
  - The zero sequence impedances are exported without considering the vector group, resulting zero sequence must be calculated separately by the user afterwards.
  - The zero sequence magnetising impedances are dependent on the wiring group, see docs at [PowerFactoryExporter - create_transformer_2w()](./powerfactory_tools/versions/pf2022/exporter/exporter.py).

- Remarks on export of `fuses`:
  - Branch like fuses are exported as switching state.
  - Element fuses does not apply a switching state by their own in PowerFactory but considered in export as applicable switching state.

- Remarks on export of the `SteadyStateCase`:
  - The operating points of the loads are specified by the controller and the associated load model in the topology for active or reactive power, see docs at [PSDM](https://github.com/ieeh-tu-dresden/power-system-data-model?tab=readme-ov-file#-general-remarks).
  - By default a consumer load has a Q-controller of type `CosPhiConst`, except in the case where active and reactive power are explicitly specified in the load flow mask in PowerFactory, then it's `QConst`.
  - It is assumed, that a station controller (if relevant) is exclusively assigned to a single generator.
  The generator itself ought to be parameterized in the same way as the station controller to ensure that the exported operating point of *Q* is the same that set by the station controller.

## <div id="tutorials" /> Tutorials

Please consider the [README](./examples/README.md) in the example section. Here, Jupyter notebooks are provided to get in touch with the usage of this toolbox:

- for export: [powerfactory_export.ipynb](./examples/powerfactory_export.ipynb)
- for control: [powerfactory_control.ipynb](./examples/powerfactory_control.ipynb)

In addition, please see this interactive example [![Code Ocean Capsule](https://codeocean.com/codeocean-assets/badge/open-in-code-ocean.svg)](https://codeocean.com/capsule/4423034/tree/v1) how to import a PSDM grid representation in `Matlab` for grid calculation purposes.

## <div id="installation" /> Installation

Install via pip:

```bash
pip install ieeh-powerfactory-tools
```

Install via pdm:

```bash
pdm add ieeh-powerfactory-tools
```

## <div id="compatibility" /> Compatibility

| Tools Version | PSDM Version | PowerFactory Version | Python Version |
|---------------|:------------:|:--------------------:|:--------------:|
| <= 1.3.1      | 1.1.0        | 2022                 | 3.9, 3.10      |
| 1.4.x         | 1.1.0        | 2022                 | 3.10           |
| 1.5.1         | 1.3.0        | 2022                 | 3.10           |
| 2.1.0         | 2.2.0        | 2022                 | 3.10           |

Starting with `PowerFactory 2023`, a new model for LV and MV loads is available as well as e.g. the result structure of harmonic load flow has changed. Also `Python 3.11` can be used. Related adjustments are on schedule for the next mayor release 3.x

## <div id="development" /> Development

### Install [pdm](https://github.com/pdm-project/pdm)

- Windows

  ```bash
  (Invoke-WebRequest -Uri https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py -UseBasicParsing).Content | python -
  ```

- Linux/Mac:

  ```bash
  curl -sSL https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py | python3 -
  ```

- Or using pipx or pip:

  ```bash
  pipx install pdm
  ```

  ```bash
  pip install --user pdm
  ```

### Clone `powerfactory-tools`

```bash
git@github.com:ieeh-tu-dresden/powerfactory-tools.git
```

```bash
cd powerfactory-tools
```

### Install `powerfactory-tools` 
- as a production tool

  ```bash
  pdm install --prod
  ```

- in development mode

  ```bash
  pdm install
  ```

For development in [Visual Studio Code](https://github.com/microsoft/vscode), all configurations are already provided:

- [ruff](https://github.com/astral-sh/ruff)
- [black](https://github.com/psf/black)
- [mypy](https://github.com/python/mypy)

## <div id="acknowledgement" /> Acknowledgement

Please note that this work is part of research activities and is still under active development.

This code was tested with `DIgSILENT PowerFactory 2021 SP5` (version < 1.4) and `DIgSILENT PowerFactory 2022 SP2`.

## <div id="attribution" /> Attribution

Please provide a link to this repository:

<https://github.com/ieeh-tu-dresden/powerfactory-tools>

Please cite as:

Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, _PowerFactory Tools - A toolbox for Python based control of DIgSILENT PowerFactory_, Zenodo, 2022. <https://doi.org/10.5281/zenodo.7074968>.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7074968.svg)](https://doi.org/10.5281/zenodo.7074968)
