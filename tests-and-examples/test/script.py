import itertools
from lammps_pythonic_wrapper import LammpsManager

# Parameters

simulation_name = "N72onH1_Heat300K"
data_filename = "../../DATA/data.N72onH1_confined"
forcefield_filename = "../../DATA/forcefield.ZonH1"

random_seed = 2017
num_molecules = 72
temperature_start = 300
temperature_stop = 300
step_per_kelvin = 1000
normal_force = -0.0455
num_steps = 1000

# Create Manager

m = LammpsManager()
u = m.getUniverse()

groups = m.createGroups({
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
    uBase.fix("freeze").arg("move linear 0.0 0.0 NULL"),
    lBase.fix("freeze").arg("move linear 0.0 0.0 0.0")
]

for g in [lBath, uBath]:
    g.temp = g.cmpt("noBiasTemp").arg("temp/com")
    g.heat = g.fix("heat").arg(
        "langevin {T1} {T2} {damp} {seed}".format(
            T1=temperature_start,
            T2=temperature_stop,
            damp=100,
            seed=random_seed
        )
    )
    init_set.extend([g.temp, g.heat, g.heat.modify("temp", g.temp.ID)])

stay_set = []
for g in [lBath, uBath]:
    tmpF = g.fix("thermostat").arg(
        "langevin {T} {T} {damp} {seed}".format(
            T=temperature_stop,
            damp=100,
            seed=random_seed
        )
    )
    stay_set.extend([g.heat.unfix, tmpF, tmpF.modify("temp", g.temp.ID)])

# Process

m.goDirectory("heating")
m.setLammps(cmdargs=["-log", "log.heating"])

# System

u.cmd("processors").arg("* * 1").e()
u.cmd("units").arg("real").e()
u.cmd("atom_style").arg("full").e()
u.cmd("dimension").arg("3").e()
u.cmd("boundary").arg("p p f").e()

u.cmd("read_data").arg(data_filename).e()

# Interaction

u.cmd("include").arg(forcefield_filename).e()

u.cmd("dielectric").arg("1.0").e()
u.cmd("pair_modify").arg("shift yes mix sixthpower").e()
u.cmd("special_bonds").arg("lj/coul 0.0 0.0 1.0").e()
u.cmd("neighbor").arg("2.0 bin").e()
u.cmd("neigh_modify").arg("delay 0 one 5000").e()
u.cmd("kspace_style").arg("pppm 1e-5").e()
u.cmd("kspace_modify").arg("slab 3.0").e()

for cmd in exclusions:
    cmd.e()

# Dynamics

u.cmd("timestep").arg("1.0").e()
u.cmd("run_style").arg("respa 2 2 bond 1 angle 2 dihedral 2 improper 2 pair 2 kspace 2").e()

# Grouping

for cmd in [g.group for g in groups if g.group]:
    cmd.e()

# Initial

for g in [lBath, lFree, uBath, uFree, liq]:
    g.fix("NVE").arg("nve").e()

for cmd in init_set:
    cmd.e()

# Monitor

u.cmd("thermo").arg(1000).e()
u.cmd("thermo_style").arg("multi").e()

for g, interval in zip([all, liq], [10000, 1000]):
    directory = "dumps_{}".format(g.ID)
    u.cmd("shell").arg("mkdir", directory).e()
    tmpD = g.dump("myDump").arg(
        "custom {inr} {dir}/atom.*.dump {args}".format(
            inr=interval,
            dir=directory,
            args="id type xu yu zu vx vy vz"
        )
    ).e()
    tmpD.modify("sort id").e()

atomK = all.cmpt("atomK").arg("ke/atom").e()
atomT = u.var("atomT").arg("atom {val}*335.514175".format(val=atomK.ref)).e()
atomVx = u.var("atomicVx").arg("atom vx").e()

for g in [all, liq]:
    chunk = g.cmpt("chunkZ").arg(
        "chunk/atom bin/1d z {orig} {d} bound z {min} {max}".format(
            orig=0.0,
            d=1.0,
            min=0.0,
            max=100.0
        )
    ).e()
    g.fix("distroZ").arg(
        "ave/chunk 1 {dur} {dur} {chunk} {vals} file {file}".format(
            dur=100000,
            chunk=chunk.ID,
            vals=" ".join([atomT.ref, atomVx.ref]),
            file="distroZ_{}.dat".format(g.ID)
        )
    ).e()

solid_values = [
    u.var("{}Fx".format(g.ID)).arg("equal fcm({},x)".format(g.ID)).e()
    for g in [lBase, lSolid, uBase, uSolid]
]

uBaseFz = u.var("uBaseFz").arg("equal fcm(uBase,z)").e()
lSurfZ, uSurfZ = [
    u.var("{}Z".format(g.ID)).arg("equal xcm({},z)".format(g.ID)).e()
    for g in [lSurf, uSurf]
]

solid_values.extend([
    uBaseFz, lSurfZ, uSurfZ,
    u.var("uFz2").arg("equal {v}*{v}".format(v=uBaseFz.ref)).e(),
    u.var("gap").arg("equal {u}-{v}".format(u=uSurfZ.ref, v=lSurfZ.ref)).e()
])

all.fix("solid_values").arg(
    "ave/time 1 {dur} {dur} {vals} file {file}".format(
        dur=1000,
        vals=" ".join([v.ref for v in solid_values]),
        file="Vals_sol.dat"
    )
).e()

liquid_values = liq.cmpt("temp").arg("temp").e()

all.fix("liquid_valuess").arg(
    "ave/time 1 {dur} {dur} {vals} file {file}".format(
        dur=1000,
        vals=liquid_values.ref,
        file="Vals_liq.dat"
    )
).e()

# Run Heat

u.cmd("log").arg("log.heat append").e()
u.cmd("run").arg((temperature_stop-temperature_start) * step_per_kelvin).e()
u.cmd("write_data").arg("data.{}_heat nocoeff".format(simulation_name)).e()

# Run Stay

u.cmd("log").arg("log.stay append").e()

for cmd in stay_set:
    cmd.e()

u.cmd("run").arg(num_steps).e()
u.cmd("write_data").arg("data.{}_stay nocoeff".format(simulation_name)).e()
