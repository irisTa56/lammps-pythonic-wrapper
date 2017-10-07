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

import sys
import time

class LammpsManager:
    """
    This class creates and accesses Universe and Group instances.
    You can specify a filename which lammps' commands will be written on.
    """

    def __init__(self, filename=None, fileheader="Lammps Simulation"):
        if filename:
            self._filename = filename
            with open(self._filename, 'w') as f:
                f.write("# {}: {}\n\n".format(fileheader, str(time.ctime())))
        else:
            self._filename = None
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

    def getGroups(self):
        return self._Groups.values()

    def getUniverse(self):
        return self._Universe

    def setFilename(self, filename):
        self._filename = filename


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
        Write the command and its arguments in lammps' format on a file.
        The filename is set as an argument of Constructor of LammpsManager.
        """
        try:
            with open(self._manager._filename, 'a') as f:
                f.write("{:15s} {}\n".format(
                    self._command, " ".join(map(str, self._args))
                ))
            return self
        except IOError:
            sys.exit("Error: Please set filename by LammpsManager.setFilename().")


class Fix(Command):
    """
    This class offers a lammps' fix command.
    """

    def __init__(self, manager, ID):
        self._ID = ID
        super().__init__(manager, "fix")
        self._unfix = self._manager._Universe.cmd("unfix").arg(self._ID)

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
