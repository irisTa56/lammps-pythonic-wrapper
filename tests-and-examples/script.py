import itertools
import subprocess
from lammps_pythonic_wrapper import LammpsManager

# Execution

input_filename = "in.shear"
#lammps_executable = "lmp_fftw"
#mpi_command = "mpirun -np 2"

# Parameters

simulation_name = "N72onEH1_ShearA"
data_filename = "../DATA/data.N72onEH1_Heat300K"
forcefield_filename = "../DATA/forcefield.ZonDia001_EH1"

random_seed = 2017
temperature = 300
num_molecules = 72
normal_force = -0.0455 # 50 MPa
num_steps = 1000 # 10000000
restart_interval = 2000000
lower_shear_velocity = 1e-05
upper_shear_velocity = 0.0

# Create Manager

m = LammpsManager(filename=input_filename)
u = m.getUniverse()

groups = m.getGroups({
    "type": {
        "lBase": 4,
        "lBath": 6,
        "lSurf": [14, 16],
        "lFree": [8, 10, 12, 14, 16],
        "uBase": 5,
        "uBath": 7,
        "uSurf": [15, 17],
        "uFree": [9, 11, 13, 15, 17]
    },
    "union": {
        "lSolid": ["lBase", "lBath", "lFree"],
        "uSolid": ["uBase", "uBath", "uFree"]
    },
    "molecule": {
        "liq": range(1, num_molecules+1)
    }
})

all, lBase, lBath, lSurf, lFree, uBase, uBath, uSurf, uFree, lSolid, uSolid, liq = groups

# Advance setting

exclusions = [
    u.cmd("neigh_modify").arg("exclude type {} {}".format(ij[0], ij[1]))
    for types in [[4, 6, 8, 10, 12, 14, 16], [5, 7, 9, 11, 13, 15, 17]]
    for ij in list(itertools.combinations_with_replacement(types, 2))
]
# Note: To write a flat nested list in Python, write for statements from outer to inner loop.

init_set = [
    uBase.fix("load").arg("aveforce NULL NULL {fz}".format(fz=normal_force)),
    uBase.fix("shearMove").arg("move linear {vel} 0.0 NULL".format(vel=upper_shear_velocity)),
    lBase.fix("shearMove").arg("move linear {vel} 0.0 0.0".format(vel=lower_shear_velocity))
]

for g in [lBath, uBath]:
    tmpC = g.cmpt("noBiasTemp").arg("temp/com")
    tmpF = g.fix("thermostat").arg(
        "langevin {T} {T} {damp} {seed}".format(
            T=temperature,
            damp=100,
            seed=random_seed
        )
    )
    init_set.extend([
        tmpC, tmpF,
        u.cmd("fix_modify").arg("{f} temp {c}".format(f=tmpF.ID, c=tmpC.ID))
    ])

# System

u.cmd("processors").arg("* * 1").w()
u.cmd("units").arg("real").w()
u.cmd("atom_style").arg("full").w()
u.cmd("dimension").arg("3").w()
u.cmd("boundary").arg("p p f").w()

u.cmd("read_data").arg(data_filename).w()

# Interaction

u.cmd("include").arg(forcefield_filename).w()

u.cmd("dielectric").arg("1.0").w()
u.cmd("pair_modify").arg("shift yes mix sixthpower").w()
u.cmd("special_bonds").arg("lj/coul 0.0 0.0 1.0").w()
u.cmd("neighbor").arg("2.0 bin").w()
u.cmd("neigh_modify").arg("delay 0 one 5000").w()
u.cmd("kspace_style").arg("pppm 1e-5").w()
u.cmd("kspace_modify").arg("slab 3.0").w()

for cmd in exclusions:
    cmd.w()

# Dynamics

u.cmd("timestep").arg("1.0").w()
u.cmd("run_style").arg("respa 2 2 bond 1 angle 2 dihedral 2 improper 2 pair 2 kspace 2").w()

# Grouping

for cmd in [g.group for g in groups if g.group]:
    cmd.w()

# Initial

for g in [lBath, lFree, uBath, uFree, liq]:
    g.fix("NVE").arg("nve").w()

for cmd in init_set:
    cmd.w()

# Monitor

u.cmd("thermo").arg(1000).w()
u.cmd("thermo_style").arg("multi").w()

for g, interval in zip([all, liq], [10000, 1000]):
    directory = "dumps_{}".format(g.ID)
    u.cmd("shell").arg("mkdir", directory).w()
    g.dump("myDump").arg(
        "custom {inr} {dir}/atom.*.dump {args}".format(
            inr=interval,
            dir=directory,
            args="id type xu yu zu vx vy vz"
        )
    ).w()

atomK = all.cmpt("atomK").arg("ke/atom").w()
atomT = u.var("atomT").arg("atom {val}*335.514175".format(val=atomK.ref)).w()
atomVx = u.var("atomicVx").arg("atom vx").w()

for g in [all, liq]:
    chunk = g.cmpt("chunkZ").arg(
        "chunk/atom bin/1d z {orig} {d} bound z {min} {max}".format(
            orig=0.0,
            d=1.0,
            min=0.0,
            max=100.0
        )
    ).w()
    g.fix("distroZ").arg(
        "ave/chunk 1 {dur} {dur} {chunk} {vals} file {file}".format(
            dur=100000,
            chunk=chunk.ID,
            vals=" ".join([atomT.ref, atomVx.ref]),
            file="distroZ_{}.dat".format(g.ID)
        )
    ).w()

solid_values = [
    u.var("{}Fx".format(g.ID)).arg("equal fcm({},x)".format(g.ID)).w()
    for g in [lBase, lSolid, uBase, uSolid]
]

uBaseFz = u.var("uBaseFz").arg("equal fcm(uBase,z)").w()
lSurfZ, uSurfZ = [
    u.var("{}Z".format(g.ID)).arg("equal xcm({},z)".format(g.ID)).w()
    for g in [lSurf, uSurf]
]

solid_values.extend([
    uBaseFz, lSurfZ, uSurfZ,
    u.var("uFz2").arg("equal {v}*{v}".format(v=uBaseFz.ref)).w(),
    u.var("gap").arg("equal {u}-{v}".format(u=uSurfZ.ref, v=lSurfZ.ref)).w()
])

all.fix("solid_values").arg(
    "ave/time 1 {dur} {dur} {vals} file {file}".format(
        dur=1000,
        vals=" ".join([v.ref for v in solid_values]),
        file="Vals_sol.dat"
    )
).w()

liquid_values = liq.cmpt("temp").arg("temp").w()

all.fix("liquid_valuess").arg(
    "ave/time 1 {dur} {dur} {vals} file {file}".format(
        dur=1000,
        vals=liquid_values.ref,
        file="Vals_liq.dat"
    )
).w()

# Run Shear

u.cmd("log").arg("log.shear append").w()
u.cmd("restart").arg("{} restart.*".format(restart_interval)).w()
u.cmd("run").arg(num_steps).w()
u.cmd("write_data").arg("data.{}_after10ns nocoeff".format(simulation_name)).w()

# Execute Lammps

#commands = mpi_command.split()
#commands.append(lammps_executable)
#commands.append("-in")
#commands.append(input_filename)
#subprocess.run(commands)

# Check whether post process can be possible

#with open("log.shear", "r") as f:
#    data = f.read()
#print("Number of lines: {}".format(len(data.split("\n"))))
