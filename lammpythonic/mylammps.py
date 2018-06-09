"""
This is *M*odified P*yLammps*, a module inheriting PyLammps class.

create: 2018/06/07 by Takayuki Kobayashi
"""

from lammps import OutputCapture, PyLammps, get_thermo_data

class MyLammps(PyLammps):

  def __init__(
    self, name="", cmdargs=None, ptr=None, comm=None, mode="nopipe"):
    """
    This constructor ...
    [Additional Arguments]
    * mode: <str>; 'nopipe', 'runzero', 'dryrun' (default 'nopipe')
    """
    super().__init__(name, cmdargs, ptr, comm)
    if mode == "nopipe":
      self.pipe_off = True
      self.run_zero = False
      self.dry_run = False
    elif mode == 'runzero':
      self.pipe_off = False
      self.run_zero = True
      self.dry_run = False
    elif mode == 'dryrun':
      self.pipe_off = False
      self.run_zero = False
      self.dry_run = True
    else:
      RuntimeError("Please set 'nopipe', 'runzero', 'dryrun' as 'mode")

  def command(self,cmd):

    if not self.dry_run:
      self.lmp.command(cmd)

    self._cmd_history.append(cmd)

  def run(self, *args, **kwargs):

    if self.pipe_off:
      return self.__getattr__('run')(*args, **kwargs)
    else:
      new_args = (0,) + args[1:] if self.run_zero else args
      return super().run(*new_args, **kwargs)

  def write_data(self, *args, **kwargs):

    if self.lmp.MPI.COMM_WORLD.rank == 0:
      self.__getattr__('write_data')(*args, **kwargs)

  def __getattr__(self, name):

    def handler(*args, **kwargs):

      cmd_args = [name] + [str(x) for x in args]

      if self.pipe_off:
        self.command(' '.join(cmd_args))

      else:

        with OutputCapture() as capture:
          self.command(' '.join(cmd_args))
          output = capture.output

        if 'verbose' in kwargs and kwargs['verbose']:
          print(output)

        lines = output.splitlines()

        if len(lines) > 1:
          return lines
        elif len(lines) == 1:
          return lines[0]

        return None

    return handler
