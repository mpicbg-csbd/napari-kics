# napari-kics

![napari-kics](https://github.com/mpicbg-csbd/napari-kics/raw/main/docs/banner.png?sanitize=true&raw=true)

[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg)](https://github.com/RichardLitt/standard-readme)
[![License](https://img.shields.io/pypi/l/napari-kics.svg?color=green)](./LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-kics.svg?color=green)](https://pypi.org/project/napari-kics)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-kics.svg?color=green)](https://python.org)
[![Python package](https://github.com/mpicbg-csbd/napari-kics/actions/workflows/python-package.yml/badge.svg)](https://github.com/mpicbg-csbd/napari-kics/actions/workflows/python-package.yml)


> A plugin to estimate chromosome sizes from karyotype images.

<small>*This [napari] plugin was generated with [Cookiecutter] using with [@napari]'s [cookiecutter-napari-plugin] template.*</small>


## Table of Contents

- Install
- Usage
- Example
- Citation
- Maintainer
- Contributing
- License


## Install

You can install `napari-kics` via [pip]:

```sh
pip install napari-kics
```

This will install all required dependencies as well. We recommend installing it in a virtual environment, e.g. using [conda]:

```sh
conda create -n kics python
conda activate kics
pip install napari-kics
```

We recommend using [mamba] as a faster alternative to conda.


## Usage

1. Launch Napari via command line (`napari`).
2. Activate the plugin via menu `Plugins -> napari-kics: Karyotype Widget`.
3. Select file via `File -> Open File`.
4. Follow instructions in the panel on the right.

You may use the interactive analysis plots directly via command line:

```sh
karyotype-analysis-plots
```


## Example

1. Launch Napari via command line (`napari`).
2. Activate the plugin via menu `Plugins -> napari-kics: Karyotype Widget`.
3. Select file via `File -> Open Sample -> napari-kics: sample`.
4. Follow instructions in the panel on the right.

Try out the interactive analysis plots directly via command line:

```sh
karyotype-analysis-plots --example
```


## Citation

> Arne Ludwig, Alexandr Dibrov, Gene Myers, Martin Pippel.
> Estimating chromosome sizes from karyotype images enables validation of
> *de novo* assemblies. To be published.


## License

Distributed under the terms of the [BSD-3] license,
"napari-kics" is free and open source software


## Issues

If you encounter any problems, please [file an issue] along with a detailed description.


## Contributing

Contributions are very welcome. Please [file a pull request] with your
contribution.

You can setup a local development environment for `napari-kics` via [pip]:

```sh
git clone https://github.com/mpicbg-csbd/napari-kics.git
cd napari-kics
pip install -e .
```


[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin
[@napari]: https://github.com/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[conda]: https://www.anaconda.com/products/distribution
[mamba]: https://github.com/mamba-org/mamba
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
[file an issue]: https://github.com/mpicbg-csbd/napari-kics/issues
[file a pull request]: https://github.com/mpicbg-csbd/napari-kics/pulls

## Overview
https://user-images.githubusercontent.com/17703905/139654249-685703b5-2196-4a73-a036-d40d578ebcdf.mp4




