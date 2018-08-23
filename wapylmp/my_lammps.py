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
    * mode: 'nopipe', 'runzero', 'runone', 'dryrun' (default 'nopipe')
    """

    super().__init__(name, cmdargs, ptr, comm)

    if mode == "nopipe":
      self.run_zero = False
      self.run_one = False
      self.dry_run = False
    elif mode == 'runzero':
      self.run_zero = True
      self.run_one = False
      self.dry_run = False
    elif mode == 'runzero':
      self.run_zero = False
      self.run_one = True
      self.dry_run = False
    elif mode == 'dryrun':
      self.run_zero = False
      self.run_one = False
      self.dry_run = True
    else:
      RuntimeError("Please set 'nopipe', 'runzero', 'runone' or "
        + "'dryrun' as 'mode'")

  def command(self,cmd):

    if not self.dry_run:
      self.lmp.command(cmd)

    self._cmd_history.append(cmd)

  def run(self, *args, **kwargs):

    if self.run_zero:
      return self.__getattr__('run')(0, *args[1:], **kwargs)
    elif self.run_one:
      return self.__getattr__('run')(1, *args[1:], **kwargs)
    else:
      return self.__getattr__('run')(*args, **kwargs)

  def __getattr__(self, name):

    def handler(*args, **kwargs):

      cmd_args = [name] + [str(x) for x in args]

      self.command(' '.join(cmd_args))

    return handler
