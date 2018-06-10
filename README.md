## Overview

To use Lammps Python Wrapper in more Python-Like way.

## Install

```
pip install git+https://github.com/irisTa56/wapylmp
```

or

```
git clone https://github.com/irisTa56/wapylmp
cd wapylmp
python setup.py install
```

## Usage

This package provides `MyLammps` class which inherits from `PyLammps` class.
`MyLammps` is different from `PyLammps` in the following three points.

* `MyLammps` can turn off `OutputCapture` capability (this might kill MPI process); by setting `mode='nopipe'` as an argument of initializer (default).
* `MyLammps` can test a simulation procedure with setting number of timesteps to 0; by setting `mode='runzero'` as an argument of initializer.
* `MyLammps` can conduct dry run in which commands will not be executed but added to the history; by setting `mode='dryrun'` as an argument of initializer.

## Acknowledgement

This project would not be possible without the following fine open-source projects.

* [lammps](https://github.com/lammps/lammps)
* [mpi4py](https://github.com/mpi4py/mpi4py)
