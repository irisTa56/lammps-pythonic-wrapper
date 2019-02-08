from mpi4py import MPI
from lammps import lammps, PyLammps, OutputCapture

class MyLammps(PyLammps):
  """
  This class inherits from PyLammps class.
  """

  def __init__(self, name="", verbose=True, **kwargs):
    """
    Only `verbose` parameter is a difference from the super.
    If `verbose` is `True`, output of *all* command executions
    will be shown in the screen after each execution is completed.
    """
    message = "\n{}\n".format("\n".join([
      "MESSAGE FROM MYLAMMPS:",
      "  You might not see progress of the simulation in screen",
      "  because Python captures standard output. To see the progress",
      "  in real time, set 'flush' keyword of 'thermo_modify' command to 'yes'.",
      "  This invokes a flush operation after thermodynamic info is written to the log file."]))

    if lammps.has_mpi4py:
      if MPI.COMM_WORLD.rank == 0:
        print(message)
    else:
      print(message)

    super().__init__(name, **kwargs)

    self._verbose = verbose

  def __getattr__(self, name):
    def handler(*args, **kwargs):
      cmd_args = [name] + [str(x) for x in args]

      with OutputCapture() as capture:
        self.command(" ".join(cmd_args))
        output = capture.output

      if self._verbose:
        print(output, end="", flush=True)

      lines = output.splitlines()

      if len(lines) > 1:
        return lines
      elif len(lines) == 1:
        return lines[0]
      return None

    return handler
