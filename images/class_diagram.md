```puml
class LammpsManager {
  +filename
  +Universe
  +Groups
  +getGroups(dict)
  +getUniverse()
}

class Universe {
  +cmd("command")
  +mol("ID")
  +reg("ID")
  +var("ID")
}

class Group {
  +group
  +cmd("command")
  +cmpt("ID")
  +dump("ID")
  +fix("ID")
}

class Command {
  -command
  -args
  +arg(*args)
  +w()
}

class Fix {
  +ID
  +unfix
}

class Compute {
  +ID
  +ref
}

class Dump {
  +ID
}

class Molecule {
  +ID
}

class Region {
  +ID
}

class Variable {
  +ID
  +ref
}

Command <|-- Fix
Command <|-- Compute
Command <|-- Dump
Command <|-- Molecule
Command <|-- Region
Command <|-- Variable

LammpsManager o-- Universe
LammpsManager o-- Group

Universe ..> Command
Universe ..> Molecule
Universe ..> Region
Universe ..> Variable

Group ..> Command
Group ..> Fix
Group ..> Compute
Group ..> Dump

Group o-- "1" Command
Fix o-- "1" Command
```
