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
    name="wapylmp",
    version="0.3.1a",
    description="Extension of Atomic Simulation Environment for LAMMPS",
    author="Takayuki Kobayashi",
    author_email="iris.takayuki@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/irisTa56/wapylmp.git",
    install_requires=["mpi4py"],
    dependency_links=['git+https://github.com/mpi4py/mpi4py.git#egg=mpi4py'],
    packages=st.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
    ),
)
