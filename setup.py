"""
This file is part of lammps-pythonic-wrapper.
Copyright (C) 2017  Takayuki Kobayashi

lammps-pythonic-wrapper is free software:
you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option)
any later version.

lammps-pythonic-wrapper is distributed in the hope that it will
be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lammps-pythonic-wrapper.
If not, see <http://www.gnu.org/licenses/>.
"""

import sys
from setuptools import setup, find_packages

# Confirm that Python can reach lammps.py
try:
  from lammps import lammps, PyLammps
except ImportError:
  print("It seems you do not have 'lammps' module.")
  print("You may need to build Lammps by CMake with a flag '-DBUILD_SHARED_LIBS=ON',")
  print("and set a path to the library directory.")
  sys.exit(1)
else:
  print("You have 'lammps' module.")

setup(
    name="lammps-pythonic-wrapper",
    version="0.0.5",
    description="To use Lammps Python Wrapper in more Python-Like way.",
    author="Takayuki Kobayashi",
    author_email="iris.takayuki@gmail.com",
    install_requires=["mpi4py>=2.0.0"],
    url="https://github.com/irisTa56/lammps-pythonic-wrapper.git",
    license="GPL",
    packages=find_packages(),
    py_modules=['lammps_pythonic_wrapper']
)

#print("Make sure a path to Lammps' shared library is in your LD_LIBRARY_PATH.")
