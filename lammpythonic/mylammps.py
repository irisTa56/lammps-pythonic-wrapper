"""
This is *M*odified P*yLammps*, a module inheriting PyLammps class.

create: 2018/06/07 by Takayuki Kobayashi
"""

from lammps import OutputCapture, PyLammps

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

    if self.dry_run:
      self._cmd_history.append(cmd)
    else:

      if cmd.startswith("run") and self.run_zero:
        cmd_dummy = " ".join(
          ["0" if i == 1 else s for i, s in enumerate(cmd.split())])
        self.lmp.command(cmd_dummy)
      else:
        self.lmp.command(cmd)

      self._cmd_history.append(cmd)

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
