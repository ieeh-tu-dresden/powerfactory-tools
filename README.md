# Powerfactory Utils

A toolbox for Python based control of DIgSILENT PowerFactory.

* [Field of Application](#application)
* [Installation](#installation)
* [Tutorials](#tutorials)
* [Acknowledgement](#acknowledgement)
* [Attribution](#attribution)
* [License](#license)

## <div id="application" /> Field of Application

This application is intended to use for an external usage ('engine mode') of the power flow calculation program [DIgSILENT PowerFactory](https://www.digsilent.de/de/powerfactory.html).
Therefore, the Python-PowerFactory-API, provided by the company, is utilized.

The following functionalities are provided:

* export of calculation relevant grid data from a PowerFactory project into three common readable JSON files utilizing predefined [schemas](./powerfactory_utils/schema):
  * grid topology
  * topology case
  * steadystate case
* [intended in future release] import from external grid data into the PowerFactory environment
* [intended in future release] basic control of PowerFactory

## <div id="tutorials" /> Tutorials

Jupyter notebooks are provided to get in touch with the usage of this toolbox:

* for export: [powerfactory_export.ipynb](./examples/powerfactory_export.ipynb)

## <div id="installation" /> Installation

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

Clone `powerfactory-utils`

```bash
git@github.com:ieeh-tu-dresden/powerfactory-utils.git
```

```bash
cd powerfactory-utils
```

Install `powerfactory-utils` as a production tool

```bash
pdm install --prod
```

Install `powerfactory-utils` in development mode

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

<https://github.com/ieeh-tu-dresden/powerfactory-utils>

Please cite as:

Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden, _Powerfactory Utils - A toolbox for Python based control of DIgSILENT PowerFactory_, Zenodo, 2022. <https://doi.org/10.5281/zenodo.7074968>.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7074968.svg)](https://doi.org/10.5281/zenodo.7074968)

## <div id="license" /> License

Copyright 2022 Institute of Electrical Power Systems and High Voltage Engineering - TU Dresden

`powerfactory-utils` is free software made available under the BSD 3-Clause License. For details see the [LICENSE](LICENSE) file.
