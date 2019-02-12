"""Submodule for MyLammps, which is inherited from ``lammps.PyLammps``."""

from mpi4py import MPI
from lammps import lammps, PyLammps, OutputCapture

class MyLammps(PyLammps):
  """PyLammps class *without* capturing outputs.

  I noticed that capturing outputs degrates computation performance
  especially on supercomputers. To avoid this problem, this class
  disables a capturing functionality of ``lammps.PyLammps`` class
  after inheriting that class. Note that, as a side effect,
  further processes using captured outputs are not available.

  """

  def run(self, *args, **kwargs):
    """Just execute ``run`` command."""
    return self.__getattr__('run')(*args, **kwargs)

  def __getattr__(self, name):
    """Override the original ``__getattr__`` not to capture outputs."""
    def handler(*args, **kwargs):
      self.command(' '.join([name] + [str(x) for x in args]))

    return handler
