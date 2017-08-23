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
import os.path

class LammpsManager:
    """
    This class creates and accesses CommandAcceptor, Universe and Group
    instances.
    It also stores IDs of lammps' values (computes and variables).
    """

    def __init__(self):
        self.CommandAcceptors = {}
        self.Universe = Universe(self)
        self.Groups = {"all": Group(self, "all")}
        self._valueDict = {}
        self._numCmd = 0

    def addCommandAcceptor(self, name):
        """
        Creates an instance of CommandAcceptor class and returns the instance.
        """
        if name in self.CommandAcceptors.keys():
            sys.exit("Error: Duplication of CommandAcceptor.")
        self.CommandAcceptors[name] = CommandAcceptor(name)
        return self.CommandAcceptors[name]

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
        A value of "None" leads to an empty group by using "group group-ID3
        type 0".
        """
        for method, groups in groupDict.items():
            for ID, members in groups.items():
                if ID in self.Groups.keys():
                    sys.exit("Error: Duplication of Group.")
                self.Groups[ID] = Group(self, ID, method, members)
        return self.Groups.values()

    def getUniverse(self):
        return self.Universe


    def getValStr(self, *args, Join=True):
        """
        Get variables and computes in the style of "v_***" or "c_***".
        This function can take both of IDs and instances of Variable/Compute.
        """
        tmpList = [
            self._valueDict[arg] + arg if isinstance(arg, str)
            else self._valueDict[arg.ID] + arg.ID for arg in args
        ]
        return " ".join(tmpList) if Join else tmpList

    def executeAll(self):
        """
        Execute all lammps' commands applied to CommandAcceptor instances in
        "Manager.CommandAcceptors" using Lammps Python Wrapper.
        """
        self.lmp = lammps()
        for setting in self.CommandAcceptors.values():
            setting.execute(self.lmp)

    def outputAll(self, filename=None, fileHeader="Lammps' Input",
                  SectionHeader=True):
        """
        Output all lammps' commands applied to CommandAcceptor instances owned
        by Manager.
        If you do not set "filename", the commands will be printed to standard
        output.
        If you set "filename" with extension of ".md" or ".markdown", the
        commands will be written in the style of markdown.
        Otherwise, the commands will be written in the style of lammps' input.
        """
        if filename:
            name, ext = os.path.splitext(filename)
            if ext in [".md", ".markdown"]:
                f = open(filename, 'w')
                f.write("# {}\n\n".format(fileHeader))
                for setting in self.CommandAcceptors.values():
                    f.write(setting._markdown())
            else:
                f = open(filename, 'w')
                f.write("# {}: {}\n\n".format(fileHeader, str(time.ctime())))
                for setting in self.CommandAcceptors.values():
                    f.write(setting._infile(SectionHeader))
        else:
            for setting in self.CommandAcceptors.values():
                setting.output(SectionHeader)

    def showAll(self):
        """
        Show IDs and commands of all lammps' commands applied to
        CommandAcceptor instances owned by Manager.
        Their arguments are not shown.
        """
        print("<CommandAcceptor>")
        for setting in self.CommandAcceptors.values():
            print(setting._name)
        print("<Commands>")
        for setting in self.CommandAcceptors.values():
            print("# {}".format(setting._name))
            setting.show()


class CommandAcceptor:
    """
    This class has lammps' commands as its properties, and outputs or executes
    the commands.
    You can assign commands in two ways:
    one is to substitute arguments in a property whose name is a command,
    something like "CommandAcceptor.run = 1000", and the other is to pass one
    or more instances of Command or its sub-class to CommandAcceptor.apply()
    method.
    """

    def __init__(self, name):
        self._name = name
        self._applyList = []
        self._sentenceDict = {}

    def apply(self, strings, *Commands):
        """
        Apply one or more instances of Command to the CommandAcceptor.
        You need to assign one or more strings to the group of the instances
        for identification; the strings can be a sentence including " ", "-",
        ",", ".", "*", "/".
        You can explain how the commands works by using the sentence.
        The sentence will be written when you call Manager.outputAll() in the
        style of markdown.
        """
        for Command in Commands:
            if Command:
                self._apply(strings, Command)

    def execute(self, lmp):
        """
        Execute all lammps' commands applied to the CommandAcceptor using
        Lammps Python rapper.
        It is also called from Manager.executeAll().
        """
        for key, val in self.__dict__.items():
            if key[0] == "_":
                continue
            if key in self._applyList:
                for cmd in val:
                    if cmd.command == "include":
                        lmp.file(cmd.args[0])
                    else:
                        lmp.command(cmd.write())
            else:
                if key == "include":
                    lmp.file(val)
                else:
                    lmp.command("{:15s} {}".format(key, val))

    def output(self, Header=False):
        """
        Print all lammps' commands applied to the CommandAcceptor to standard
        output.
        It is also called from Manager.outputAll().
        """
        if Header:
            print("# {}".format(self._name))
            print("")
        exkey = None
        for key, val in self.__dict__.items():
            if key[0] == "_":
                continue
            if exkey and (exkey in self._applyList or key in self._applyList):
                print("")
            if key in self._applyList:
                for cmd in val:
                    print(cmd.write())
            else:
                print("{:15s} {}".format(key, val))
            exkey = key
        print("")

    def show(self):
        """
        Show IDs and commands of all lammps' commands applied to the
        CommandAcceptor.
        It is also called from Manager.showAll().
        """
        for key, val in self.__dict__.items():
            if key[0] == "_":
                continue
            if key in self._applyList:
                for cmd in val:
                    print("ID: {} | Command: {}".format(cmd.ID, cmd.command))
            else:
                print("ID: None | Command: {}".format(key))

    def _apply(self, strings, Command):
        key = strings
        for tup in [(ch, "") for ch in [" ", "-", ",", ".", "*", "/"]]:
            key = key.replace(tup[0], tup[1])
        if key in self._applyList:
            exec("self.{}.append(Command)".format(key))
        else:
            if key in self.__dict__:
                sys.exit("Error: Duplication of Apply.")
            exec("self.{} = [Command]".format(key))
            self._applyList.append(key)
            self._sentenceDict[key] = strings

    def _infile(self, Header=False):
        commands = ["# {}".format(self._name), ""] if Header else []
        exkey = None
        for key, val in self.__dict__.items():
            if key[0] == "_":
                continue
            if exkey and (exkey in self._applyList or key in self._applyList):
                commands.append("")
            if key in self._applyList:
                for cmd in val:
                    commands.append(cmd.write())
            else:
                commands.append("{:15s} {}".format(key, val))
            exkey = key
        commands.append("\n")
        return "\n".join(commands)

    def _markdown(self):
        lines = ["## {}".format(self._name), ""]
        inCode = False
        exkey = None
        for key, val in self.__dict__.items():
            if key[0] == "_":
                continue
            if exkey and (exkey in self._applyList or key in self._applyList):
                if inCode:
                    lines.append("```")
                    inCode = False
                lines.append("")
            if key in self._applyList:
                lines.extend[self._sentenceDict[key], "", "```"]
                for cmd in val:
                    lines.append(cmd.write())
                lines.append("```")
            else:
                if not inCode:
                    inCode = True
                    lines.append("```")
                lines.append("{:15s} {}".format(key, val))
            exkey = key
        if inCode:
            lines.append("```")
        lines.append("\n")
        return "\n".join(lines)


class Universe:
    """
    This class creates and accesses instances of Command or its sub-class which
    is not associated with any particular group.
    You can access the instances through dictionaries using their ID as a key.
    """

    def __init__(self, manager):
        self._manager = manager
        self.cmds = {}
        self.mols = {}
        self.regs = {}
        self.vars = {}

    def cmd(self, command, *args, ID=None):
        """
        Add an instance of Command, which is not associated with any particular
        group, to Universe.
        """
        if not ID:
            ID = command + str(len(self.cmds))
        self.cmds[ID] = Command(self._manager, command, ID, *args)
        return self.cmds[ID]

    def mol(self, ID, *args):
        """
        Add an instance of Molecule to Universe.
        """
        args = [ID] + list(args)
        self.mols[ID] = Molecule(self._manager, ID, *args)
        return self.mols[ID]

    def reg(self, ID, *args):
        """
        Add an instance of Region to Universe.
        """
        args = [ID] + list(args)
        self.regs[ID] = Region(self._manager, ID, *args)
        return self.regs[ID]

    def var(self, ID, *args):
        """
        Add an instance of Variable to Universe.
        """
        args = [ID] + list(args)
        self.vars[ID] = Variable(self._manager, ID, *args)
        self._manager._valueDict[ID] = "v_"
        return self.vars[ID]


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
        self.ID = ID
        self.cmds = {}
        self.fixes = {}
        self.cmpts = {}
        self.dumps = {}
        if method and members:
            self.group = self.cmd("group", "{} {}".format(
                method, " ".join(map(str, members))
                if hasattr(members, '__iter__') and not isinstance(members, str)
                else str(members)
            ))
        elif method and not members:
            self.group = self.cmd("group", "type 0")
        else:
            self.group = None

    def cmd(self, command, *args, ID=None):
        """
        Add an instance of Command, which is associated with a particular
        group, to Group.
        """
        self._manager._numCmd += 1
        if not ID:
            ID = command + str(len(self.cmds))
        args = [self.ID] + list(args)
        self.cmds[ID] = Command(self._manager, command, ID, *args)
        return self.cmds[ID]

    def cmpt(self, ID, *args):
        """
        Add an instance of Compute to Group.
        """
        fullID = "{}_{}".format(ID, self.ID)
        args = [fullID, self.ID] + list(args)
        self.cmpts[ID] = Compute(self._manager, fullID, *args)
        self._manager._valueDict[fullID] = "c_"
        return self.cmpts[ID]

    def dump(self, ID, *args):
        """
        Add an instance of Dump to Group.
        """
        fullID = "{}_{}".format(ID, self.ID)
        args = [fullID, self.ID] + list(args)
        self.dumps[ID] = Dump(self._manager, fullID, *args)
        return self.dumps[ID]

    def fix(self, ID, *args):
        """
        Add an instance of Fix to Group.
        """
        fullID = "{}_{}".format(ID, self.ID)
        args = [fullID, self.ID] + list(args)
        self.fixes[ID] = Fix(self._manager, fullID, *args)
        return self.fixes[ID]


class Command:
    """
    This class offers any kind of lammps' command which does not have its own
    ID in the lammps syntax.
    """

    def __init__(self, manager, command, ID, *args):
        self._manager = manager
        self.command = command
        self.ID = ID
        self.args = args

    def write(self):
        return "{:15s} {}".format(self.command, " ".join(map(str, self.args)))


class Fix(Command):
    """
    This class offers a lammps' fix command.
    """

    def __init__(self, manager, ID, *args):
        super().__init__(manager, "fix", ID, *args)
        self.unfix = self._manager.Universe.cmd(
            "unfix", self.ID, ID="UN_{}".format(self.ID)
        )


class Compute(Command):
    """
    This class offers a lammps' compute command.
    """

    def __init__(self, manager, ID, *args):
        super().__init__(manager, "compute", ID, *args)


class Dump(Command):
    """
    This class offers a lammps' dump command.
    """

    def __init__(self, manager, ID, *args):
        super().__init__(manager, "dump", ID, *args)


class Molecule(Command):
    """
    This class offers a lammps' molecule command.
    """

    def __init__(self, manager, ID, *args):
        super().__init__(manager, "molecule", ID, *args)


class Region(Command):
    """
    This class offers a lammps' region command.
    """

    def __init__(self, manager, ID, *args):
        super().__init__(manager, "region", ID, *args)


class Variable(Command):
    """
    This class offers a lammps' variable command.
    """

    def __init__(self, manager, ID, *args):
        super().__init__(manager, "variable", ID, *args)
