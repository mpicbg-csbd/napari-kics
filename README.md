# napari-karyotype

![napari-karyotype](./docs/banner.png?sanitize=true&raw=true)

[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)
[![License](https://img.shields.io/pypi/l/napari-karyotype.svg?color=green)](./LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-karyotype.svg?color=green)](https://pypi.org/project/napari-karyotype)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-karyotype.svg?color=green)](https://python.org)
[![tests](https://github.com/adibrov/napari-karyotype/workflows/tests/badge.svg)](https://github.com/adibrov/napari-karyotype/actions)
[![codecov](https://codecov.io/gh/adibrov/napari-karyotype/branch/master/graph/badge.svg)](https://codecov.io/gh/adibrov/napari-karyotype)


> A plugin to evaluate the relative chromosome sizes from karyotype images and
> compare them to scaffold sizes.

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

You can install `napari-karyotype` via [pip]:

```sh
git clone git@github.com:mpicbg-csbd/napari-karyotype.git
cd napari-karyotype
pip install -e .
```


## Usage

1. Launch Napari via command line (`napari`).
2. Activate the plugin via menu `Plugins -> napari-karyotype: Karyotype Widget`.
3. Select file via `File -> Open File`.
4. Follow instructions in the panel on the right.

You may use the interactive analysis plots directly via command line:

```sh
karyotype-analysis-plots
```


## Example

1. Launch Napari via command line (`napari`).
2. Activate the plugin via menu `Plugins -> napari-karyotype: Karyotype Widget`.
3. Select file via `File -> Open Sample -> napari-karyotype: sample`.
4. Follow instructions in the panel on the right.

Try out the interactive analysis plots directly via command line:

```sh
karyotype-analysis-plots --example
```


## License

Distributed under the terms of the [BSD-3] license,
"napari-karyotype" is free and open source software


## Issues

If you encounter any problems, please [file an issue] along with a detailed description.


## Contributing

Contributions are very welcome. Please [file a pull request] with your
contribution.
<!-- Tests can be run with [tox], please ensure the coverage at least stays the same before you submit a pull request. -->


[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin
[@napari]: https://github.com/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
[file an issue]: https://github.com/mpicbg-csbd/napari-karyotype/issues
[file a pull request]: https://github.com/mpicbg-csbd/napari-karyotype/pulls

## Overview
https://user-images.githubusercontent.com/17703905/139654249-685703b5-2196-4a73-a036-d40d578ebcdf.mp4




