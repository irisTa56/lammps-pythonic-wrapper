## Overview

To use Lammps Python Wrapper in more Python-Like way.

## Install

```
pip install git+https://github.com/irisTa56/lammps-pythonic-wrapper
```

or

```
git clone https://github.com/irisTa56/lammps-pythonic-wrapper
cd lammps-pythonic-wrapper
python setup.py install
```

Please make sure a path to the directory containing Lammps' shared library is in your LD_LIBRARY_PATH. For details, please see [this section in lammps' manual](http://lammps.sandia.gov/doc/Section_python.html#installing-the-python-wrapper-into-python).

## Usage

```
python script.py
```

Please see "tests-and-examples" directory for example(s) of "script.py".

## Acknowledgement

This project would not be possible without many fine open-source projects.

* [mpi4py](https://github.com/mpi4py/mpi4py)
* [lammps](https://github.com/lammps/lammps)

## To Do

* Simple example
