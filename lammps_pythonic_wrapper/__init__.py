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

import os
import sys
import time

from mpi4py import MPI

from .lammps import lammps, PyLammps

class LammpsManager:
  """
  This class creates and accesses Universe and Group instances.
  You can specify a filename which lammps' commands will be written on.
  """

  def __init__(self, filename=None, fileheader=None, lammps_interface=None, cmdargs=None):
    self._comm = MPI.COMM_WORLD
    # Lammps' input file
    if filename:
      self._filename = filename
      with open(self._filename, 'w') as f:
        f.write("# {}: {}\n\n".format(fileheader, str(time.ctime())))
    else:
      self._filename = None
    # Interface to Lammps
    if lammps_interface == "lammps":
      self._Lammps = lammps(cmdargs=cmdargs)
    elif lammps_interface == "PyLammps":
      self._Lammps = PyLammps(cmdargs=cmdargs)
    else:
      self._Lammps = None
    #
    self._Universe = Universe(self)
    self._Groups = {"all": Group(self, "all")}

  def createGroups(self, groupDict):
    """
    Creates instances of Group class and returns the instances.
    The instances are defined by a dectipnary like the following.
      {
        "style": {
          "group-ID1": [member1, member2, ...]
          "group-ID2": member
          "group-ID3": None
        }
      }
    A value of "None" leads to an empty group by using lammps' command of
    "group group-ID3 type 0".
    """
    for method, groups in groupDict.items():
      for ID, members in groups.items():
        if ID in self._Groups.keys():
          sys.exit("Error: Duplication of Group.")
        self._Groups[ID] = Group(self, ID, method, members)
    return self._Groups.values()

  def getGroups(self):
    return self._Groups.values()

  def getLammps(self):
    return self._Lammps

  def getUniverse(self):
    return self._Universe

  def goBack(self):
    os.chdir("..")

  def goDirectory(self, directory):
    """
    Make & Change directory while taking MPI into account.
    """
    if self._comm.Get_rank() == 0:
      if not os.path.exists(directory):
        os.mkdir(directory)
    self._comm.Barrier()
    os.chdir(directory)

  def setFile(self, filename="in.lammps", fileheader=None):
    self._filename = filename
    with open(self._filename, 'w') as f:
      f.write("# {}: {}\n\n".format(fileheader, str(time.ctime())))

  def setLammps(self, lammps_interface="lammps", cmdargs=None, delete_previous=True):
    if delete_previous and self._Lammps:
      del self._Lammps
    if lammps_interface == "lammps":
      self._Lammps = lammps(cmdargs=cmdargs)
    elif lammps_interface == "PyLammps":
      self._Lammps = PyLammps(cmdargs=cmdargs)
    else:
      sys.exit("There is no such an interface to lammps.")


class Universe:
  """
  This class creates and accesses instances of Command or its sub-class which
  is not associated with any particular group.
  You can access the instances through dictionaries using their ID as a key.
  """

  def __init__(self, manager):
    self._manager = manager

  def cmd(self, command):
    """
    Add an instance of Command, which is not associated with any particular
    group, to Universe.
    """
    return Command(self._manager, command)

  def mol(self, ID):
    """
    Add an instance of Molecule to Universe.
    """
    return Molecule(self._manager, ID).arg(ID)

  def reg(self, ID):
    """
    Add an instance of Region to Universe.
    """
    return Region(self._manager, ID).arg(ID)

  def var(self, ID):
    """
    Add an instance of Variable to Universe.
    """
    return Variable(self._manager, ID).arg(ID)


class Group:
  """
  This class creates and accesses instances of Command or its sub-class which
  is associated with a particular group.
  This class has an ID which corresponds to lammps' group-ID.
  You can access Command instances through dictionaries.
  Keys of the dictionaries is not ID of the Command instances iteslf, but
  without a group's name;
  ID of a Command instance created by Group instance named "foo" is something
  like "cmd1_foo", however the Command instance can be accessed by using
  foo.commands["cmd1"].
  """

  def __init__(self, manager, ID, method=None, members=None):
    self._manager = manager
    self._ID = ID
    if method and members:
       self._group = self.cmd("group").arg("{} {}".format(
        method, " ".join(map(str, members))
        if hasattr(members, '__iter__') and not isinstance(members, str)
        else str(members)
      ))
    elif method and not members:
      self._group = self.cmd("group").arg("type 0")
    else:
      self._group = None

  @property
  def ID(self):
    return self._ID

  @property
  def group(self):
    return self._group

  def cmd(self, command):
    """
    Add an instance of Command, which is associated with a particular
    group, to Group.
    """
    return Command(self._manager, command).arg(self._ID)

  def cmpt(self, ID):
    """
    Add an instance of Compute to Group.
    """
    fullID = "{}_{}".format(ID, self._ID)
    return Compute(self._manager, fullID).arg(fullID, self._ID)

  def dump(self, ID, *args):
    """
    Add an instance of Dump to Group.
    """
    fullID = "{}_{}".format(ID, self._ID)
    return Dump(self._manager, fullID).arg(fullID, self._ID)

  def fix(self, ID, *args):
    """
    Add an instance of Fix to Group.
    """
    fullID = "{}_{}".format(ID, self._ID)
    return Fix(self._manager, fullID).arg(fullID, self._ID)


class Command:
  """
  This class offers any kind of lammps' command which does not have its own
  ID in the lammps syntax except for "group".
  """

  def __init__(self, manager, command):
    self._manager = manager
    self._command = command
    self._args = []

  def arg(self, *args):
    """
    Set arguments for the command.
    """
    self._args += args
    return self

  def w(self):
    """
    Write the command and its arguments in lammps' format.
    """
    try:
      with open(self._manager._filename, 'a') as f:
        f.write("{:15s} {}\n".format(
          self._command, " ".join(map(str, self._args))
        ))
      return self
    except IOError:
      sys.exit("Error: Please set filename by LammpsManager.setFile().")

  def e(self):
    """
    Pass the command to the interface to Lammps.
    """
    if self._command == "include":
      with open(self._args[0], "r") as f:
        data = f.read()
      lines = data.split("\n")
      for line in lines:
        if line:
          if not line[0] == "#":
            try:
              self._manager._Lammps.command(line)
            except AttributeError:
              sys.exit("Error: Please set interface by LammpsManager.setLammps().")
    else:
      try:
        self._manager._Lammps.command("{:15s} {}".format(
          self._command, " ".join(map(str, self._args))
        ))
        return self
      except AttributeError:
        sys.exit("Error: Please set interface by LammpsManager.setLammps().")


class Fix(Command):
  """
  This class offers a lammps' fix command.
  """

  def __init__(self, manager, ID):
    self._ID = ID
    super().__init__(manager, "fix")
    self._unfix = self._manager._Universe.cmd("unfix").arg(self._ID)

  def modify(self, *args):
    return self._manager._Universe.cmd("fix_modify").arg(self._ID, *args)

  @property
  def ID(self):
    return self._ID

  @property
  def unfix(self):
    return self._unfix


class Compute(Command):
  """
  This class offers a lammps' compute command.
  """

  def __init__(self, manager, ID):
    self._ID = ID
    self._ref = "c_" + ID
    super().__init__(manager, "compute")

  def modify(self, *args):
    return self._manager._Universe.cmd("compute_modify").arg(self._ID, *args)

  @property
  def ID(self):
    return self._ID

  @property
  def ref(self):
    return self._ref


class Dump(Command):
  """
  This class offers a lammps' dump command.
  """

  def __init__(self, manager, ID):
    self._ID = ID
    super().__init__(manager, "dump")

  def modify(self, *args):
    return self._manager._Universe.cmd("dump_modify").arg(self._ID, *args)

  @property
  def ID(self):
    return self._ID


class Molecule(Command):
  """
  This class offers a lammps' molecule command.
  """

  def __init__(self, manager, ID):
    self._ID = ID
    super().__init__(manager, "molecule")

  @property
  def ID(self):
    return self._ID


class Region(Command):
  """
  This class offers a lammps' region command.
  """

  def __init__(self, manager, ID):
    self._ID = ID
    super().__init__(manager, "region")

  @property
  def ID(self):
    return self._ID


class Variable(Command):
  """
  This class offers a lammps' variable command.
  """

  def __init__(self, manager, ID):
    self._ID = ID
    self._ref = "v_" + ID
    super().__init__(manager, "variable")

  @property
  def ID(self):
    return self._ID

  @property
  def ref(self):
    return self._ref
