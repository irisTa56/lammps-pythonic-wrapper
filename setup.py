import os
import sys
from pip._internal import main as pip_main
from setuptools import setup, find_packages


try:
  from lammps import lammps, PyLammps
except ImportError:
  print("It seems that you don't have 'lammps' module.")
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


with open("README.md", "r") as f:
  long_description = f.read()

version_ns = {}
with open(os.path.join("wapylmp", "_version.py")) as f:
  exec(f.read(), {}, version_ns)

setup(
  name="wapylmp",
  version=version_ns["__version__"],
  description="My little wrapper for PyLammps",
  author="Takayuki Kobayashi",
  author_email="iris.takayuki@gmail.com",
  long_description=long_description,
  long_description_content_type="text/markdown",
  url="https://github.com/irisTa56/wapylmp.git",
  packages=find_packages(),
  classifiers=(
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: GNU General Public License (GPL)"))
