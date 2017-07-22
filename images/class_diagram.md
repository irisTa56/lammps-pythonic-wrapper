```puml
class Manager {
  +Settings
  +Universe
  +Groups
  +addSetting()
  +createGroups()
  +getValStr()
  +executeAll()
  +outputAll()
  +showAll()
}

class Setting {
  +__dict__
  +apply()
  +execute()
  +output()
  +show()
}

class Universe {
  +addCmd()
  +addMol()
  +addReg()
  +addVar()
}

class Group {
  +group
  +addCmd()
  +addCmpt()
  +addDump()
  +addFix()
}

class Command {
  -command
  -args
  +ID
  #write()
}

class Fix {
  +unfix
}

class Compute

class Dump

class Region

class Variable

Command <|-- Fix
Command <|-- Compute
Command <|-- Dump
Command <|-- Molecule
Command <|-- Region
Command <|-- Variable

Manager o-- Setting
Manager o-- Universe
Manager o-- Group

Universe o-- Command
Universe o-- Molecule
Universe o-- Region
Universe o-- Variable

Group o-- Command
Group o-- Fix
Group o-- Compute
Group o-- Dump

Group o-- "1" Command
Fix o-- "1" Command

Setting ..> Command : use
```
