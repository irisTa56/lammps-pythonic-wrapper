import sys
from pip._internal import main as pip_main
from setuptools import setup, find_packages


try:
  from lammps import lammps, PyLammps
except ImportError:
  print("It seems you do not have 'lammps' module.")
  print("You may need to build Lammps by CMake with a flag '-DBUILD_SHARED_LIBS=ON',")
  print("and set a path to the library directory.")
  sys.exit(1)


try:
  import mpi4py
except ImportError:
  print("Get and build mpi4py...")

  pip_command = ["install"]
  if "--user" in sys.argv:
    pip_command.append("--user")
  pip_command.append("git+https://github.com/mpi4py/mpi4py.git")

  pip_main(pip_command)


with open("README.md", "r") as fh:
  long_description = fh.read()

setup(
  name="wapylmp",
  version="0.3.1a",
  description="Extension of Atomic Simulation Environment for LAMMPS",
  author="Takayuki Kobayashi",
  author_email="iris.takayuki@gmail.com",
  long_description=long_description,
  long_description_content_type="text/markdown",
  url="https://github.com/irisTa56/wapylmp.git",
  packages=find_packages(),
  classifiers=(
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: GNU General Public License (GPL)",
  ),
)
