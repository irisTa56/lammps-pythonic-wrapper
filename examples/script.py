# 3d Lennard-Jones melt

from lammps_pythonic_wrapper import LammpsManager

# Parameters
step = 100
xx = 20
yy = 20
zz = 20

m = LammpsManager(name="open") # Assume that your machine name is 'open'
u = m.getUniverse()

a, = m.getGroups()

box_reg = u.reg("box").arg(
  "block", "0 {x} 0 {y} 0 {z}".format(x=xx, y=yy, z=zz)
)
box = u.cmd("create_box").arg(1, box_reg.ID)

commands = [
  u.cmd("units").arg("lj"),
  u.cmd("atom_style").arg("atomic"),
  u.cmd("lattice").arg("fcc", 0.8442),
  box_reg, box,
  u.cmd("create_atoms").arg(1, "box"),
  u.cmd("mass").arg(1, 1.0),
  a.cmd("velocity").arg("create", 1.44, 87287, "loop", "geom"),
  u.cmd("pair_style").arg("lj/cut", 2.5),
  u.cmd("pair_coeff").arg(1, 1, 1.0, 1.0, 2.5),
  u.cmd("neighbor").arg(0.3, "bin"),
  u.cmd("neigh_modify").arg("delay", 0, "every", 20, "check", "no"),
  a.fix("ensemble").arg("nve"),
  u.cmd("run").arg(step)
]

for cmd in commands:
  cmd.e()
