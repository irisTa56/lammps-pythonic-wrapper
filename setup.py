import sys
import setuptools as st

try:
  from lammps import lammps, PyLammps
except ImportError:
  print("It seems you do not have 'lammps' module.")
  print("You may need to build Lammps by CMake with a flag '-DBUILD_SHARED_LIBS=ON',")
  print("and set a path to the library directory.")
  sys.exit(1)

with open("README.md", "r") as fh:
    long_description = fh.read()

st.setup(
    name="lammpythonic",
    version="0.1a.1",
    description="Extension of Atomic Simulation Environment for LAMMPS",
    author="Takayuki Kobayashi",
    author_email="iris.takayuki@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/irisTa56/lammpythonic.git",
    packages=st.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
    ),
    install_requires=["mpi4py>=2.0.0"],
)
