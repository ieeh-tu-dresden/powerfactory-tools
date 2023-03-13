# IEEH PowerFactory Tools

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

A toolbox for Python based control of DIgSILENT PowerFactory.

- [IEEH PowerFactory Tools](#ieeh-powerfactory-tools)
  - [ Field of Application](#-field-of-application)
  - [ Tutorials](#-tutorials)
  - [ Installation](#-installation)
  - [ Compatibility](#-compatibility)
  - [ Development](#-development)
  - [ Acknowledgement](#-acknowledgement)
  - [ Attribution](#-attribution)

## <div id="application" /> Field of Application

This application is intended to use for an external usage ('engine mode') of the power flow calculation program [DIgSILENT PowerFactory](https://www.digsilent.de/de/powerfactory.html).
Therefore, the Python-PowerFactory-API, provided by the company, is utilized.

The following functionalities are provided:

* export of calculation relevant grid data from a PowerFactory project into three common readable JSON files utilizing predefined [schemas](./powerfactory_tools/schema):
  * grid topology:
    * base topology containing all elements of the exported grid
  * topology case;
    * information about disabled elements to represent a specific operational case based on the base topology
  * steadystate case
    * information about power draw/infeed for a specific operational case
* [intended in future release] import from external grid data into the PowerFactory environment
* [intended in future release] basic control of PowerFactory

## <div id="tutorials" /> Tutorials

Jupyter notebooks are provided to get in touch with the usage of this toolbox:

* for export: [powerfactory_export.ipynb](./examples/powerfactory_export.ipynb)

## <div id="installation" /> Installation

Just install via pip:

```bash
pip install ieeh-powerfactory-tools
```

## <div id="compatibility" /> Compatibility

Due to very useful features in `python 3.10+` - which is supported by `PowerFactory 2022`, we decided to drop `python 3.9` starting from version `1.4`. Users that use an older `PowerFactory` version, please use version `1.3`.

## <div id="development" /> Development

Install [pdm](https://github.com/pdm-project/pdm)

Windows:

```bash
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py -UseBasicParsing).Content | python -
```

Linux/Mac:

```bash
curl -sSL https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py | python3 -
```

Install [pdm-venv](https://github.com/pdm-project/pdm-venv)

```bash
pdm plugin add pdm-venv
pdm config venv.in_project true
```

Clone `powerfactory-tools`

```bash
git@github.com:ieeh-tu-dresden/powerfactory-tools.git
```

```bash
cd powerfactory-tools
```

Install `powerfactory-tools` as a production tool

```bash
pdm install --prod
```

Install `powerfactory-tools` in development mode

```bash
pdm install
```

For development in [Visual Studio Code](https://github.com/microsoft/vscode), all configurations are already provided:

* [flake8](https://github.com/PyCQA/flake8)
* [black](https://github.com/psf/black)
* [mypy](https://github.com/python/mypy)

## <div id="acknowledgement" /> Acknowledgement

Please note that this work is part of research activities and is still under active development.

This code was tested with `DIgSILENT PowerFactory 2021 SP5` and `DIgSILENT PowerFactory 2022 SP2`.

## <div id="attribution" /> Attribution

Please provide a link to this repository:

<https://github.com/ieeh-tu-dresden/powerfactory-tools>

Please cite as:

Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, _PowerFactory Tools - A toolbox for Python based control of DIgSILENT PowerFactory_, Zenodo, 2022. <https://doi.org/10.5281/zenodo.7074968>.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7074968.svg)](https://doi.org/10.5281/zenodo.7074968)