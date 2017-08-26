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

from lammps import lammps
import sys
import time

class LammpsManager:
    """
    This class creates and accesses Universe and Group instances.
    You can specify a filename which lammps' commands will be written on.
    """

    def __init__(self, filename=None, fileheader="Lammps Simulation"):
        if filename:
            self.filename = filename
            with open(self.filename, 'w') as f:
                f.write("# {}: {}\n\n".format(fileheader, str(time.ctime())))
        self.Universe = Universe(self)
        self.Groups = {"all": Group(self, "all")}

    def getGroups(self, groupDict):
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
                if ID in self.Groups.keys():
                    sys.exit("Error: Duplication of Group.")
                self.Groups[ID] = Group(self, ID, method, members)
        return self.Groups.values()

    def getUniverse(self):
        return self.Universe


class Universe:
    """
    This class creates and accesses instances of Command or its sub-class which
    is not associated with any particular group.
    You can access the instances through dictionaries using their ID as a key.
    """

    def __init__(self, manager):
        self.manager = manager

    def cmd(self, command):
        """
        Add an instance of Command, which is not associated with any particular
        group, to Universe.
        """
        return Command(self.manager, command)

    def mol(self, ID):
        """
        Add an instance of Molecule to Universe.
        """
        return Molecule(self.manager, ID).arg(ID)

    def reg(self, ID):
        """
        Add an instance of Region to Universe.
        """
        return Region(self.manager, ID).arg(ID)

    def var(self, ID):
        """
        Add an instance of Variable to Universe.
        """
        return Variable(self.manager, ID).arg(ID)


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
        self.manager = manager
        self.ID = ID
        if method and members:
             self.group = self.cmd("group").arg("{} {}".format(
                method, " ".join(map(str, members))
                if hasattr(members, '__iter__') and not isinstance(members, str)
                else str(members)
            ))
        elif method and not members:
            self.group = self.cmd("group").arg("type 0")
        else:
            self.group = None

    def cmd(self, command):
        """
        Add an instance of Command, which is associated with a particular
        group, to Group.
        """
        return Command(self.manager, command).arg(self.ID)

    def cmpt(self, ID):
        """
        Add an instance of Compute to Group.
        """
        fullID = "{}_{}".format(ID, self.ID)
        return Compute(self.manager, fullID).arg(fullID, self.ID)

    def dump(self, ID, *args):
        """
        Add an instance of Dump to Group.
        """
        fullID = "{}_{}".format(ID, self.ID)
        return Dump(self.manager, fullID).arg(fullID, self.ID)

    def fix(self, ID, *args):
        """
        Add an instance of Fix to Group.
        """
        fullID = "{}_{}".format(ID, self.ID)
        return Fix(self.manager, fullID).arg(fullID, self.ID)


class Command:
    """
    This class offers any kind of lammps' command which does not have its own
    ID in the lammps syntax except for "group".
    """

    def __init__(self, manager, command):
        self.manager = manager
        self.command = command
        self.args = []

    def arg(self, *args):
        """
        Set arguments for the command.
        """
        self.args += args
        return self

    def w(self):
        """
        Write the command and its arguments in lammps' format on a file.
        The filename is set as an argument of Constructor of LammpsManager.
        """
        try:
            with open(self.manager.filename, 'a') as f:
                f.write("{:15s} {}\n".format(
                    self.command, " ".join(map(str, self.args))
                ))
            return self
        except:
            print("Error: Please set filename in creating LammpsManager instance.")


class Fix(Command):
    """
    This class offers a lammps' fix command.
    """

    def __init__(self, manager, ID):
        self.ID = ID
        super().__init__(manager, "fix")
        self.unfix = self.manager.Universe.cmd("unfix").arg(self.ID)


class Compute(Command):
    """
    This class offers a lammps' compute command.
    """

    def __init__(self, manager, ID):
        self.ID = ID
        self.ref = "c_" + ID
        super().__init__(manager, "compute")


class Dump(Command):
    """
    This class offers a lammps' dump command.
    """

    def __init__(self, manager, ID):
        self.ID = ID
        super().__init__(manager, "dump")


class Molecule(Command):
    """
    This class offers a lammps' molecule command.
    """

    def __init__(self, manager, ID):
        self.ID = ID
        super().__init__(manager, "molecule")


class Region(Command):
    """
    This class offers a lammps' region command.
    """

    def __init__(self, manager, ID):
        self.ID = ID
        super().__init__(manager, "region")


class Variable(Command):
    """
    This class offers a lammps' variable command.
    """

    def __init__(self, manager, ID):
        self.ID = ID
        self.ref = "v_" + ID
        super().__init__(manager, "variable")
