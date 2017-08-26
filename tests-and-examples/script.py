import itertools as it
from lammps_pythonic_wrapper import LammpsManager

# Parameters

SimulationName = "N72onH1_Heat300K"

DataFileName = "../DATA/data.N72onEH1_confined"
ForceFieldFileName = "../DATA/forcefield.ZonH1"

RandomSeed = 2017
NumMolecules = 72
TemperatureStart = 300
TemperatureStop = 500
StepPerKelvin = 1000
NormalForce = -0.0455 # 50 MPa
NumSteps = 2000000

# Create Manager

m = LammpsManager(filename="in.heat")
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
        "liq": range(1, NumMolecules + 1)
    }
})

all, lBase, lBath, lSurf, lFree, uBase, uBath, uSurf, uFree, lSolid, uSolid, liq = groups

# Advance setting

exclusions = [
    u.cmd("neigh_modify").arg("exclude type {} {}".format(ij[0], ij[1]))
    for types in [[4, 6, 8, 10, 12, 14, 16], [5, 7, 9, 11, 13, 15, 17]]
    for ij in list(it.combinations_with_replacement(types, 2))
]

initSet = [lBase.fix("freeze").arg("setforce 0.0 0.0 0.0")]

initSet.append(uBase.fix("load").arg(
    "aveforce NULL NULL {fz}".format(fz=NormalForce)
))
initSet.append(uBase.fix("freeZ").arg("setforce 0.0 0.0 NULL"))

initSet.append(uBase.cmpt("tempZ").arg("temp/partial 0 0 1"))
initSet.append(uBase.fix("damper").arg(
    "langevin 0 0 {damp} {seed}".format(damp=100, seed=RandomSeed)
))
initSet.append(u.cmd("fix_modify").arg(
    "{fix} temp {cmpt}".format(fix=initSet[-1].ID, cmpt=initSet[-2].ID)
))

noBiasT = {}
heat = {}

for g in [lBath, uBath]:
    noBiasT[g.ID] = g.cmpt("noBiasTemp").arg("temp/com")
    heat[g.ID]  = g.fix("heat").arg("langevin {T1} {T2} {damp} {seed}".format(
        T1=TemperatureStart, T2=TemperatureStop, damp=100, seed=RandomSeed
    ))
    initSet.extend([noBiasT[g.ID], heat[g.ID], u.cmd("fix_modify").arg(
        "{fix} temp {cmpt}".format(fix=heat[g.ID].ID, cmpt=noBiasT[g.ID].ID)
    )])

staySet = []
for g in [lBath, uBath]:
    staySet.append(heat[g.ID].unfix)
    staySet.append(g.fix("thermo").arg("langevin {T} {T} {damp} {seed}".format(
        T=TemperatureStop, damp=100, seed=RandomSeed
    )))
    staySet.append(u.cmd("fix_modify").arg("{fix} temp {cmpt}".format(
        fix=staySet[-1].ID, cmpt=noBiasT[g.ID].ID
    )))

# System

u.cmd("processors").arg("* * 1").w()
u.cmd("units").arg("real").w()
u.cmd("atom_style").arg("full").w()
u.cmd("dimension").arg("3").w()
u.cmd("boundary").arg("p p f").w()

u.cmd("read_data").arg(DataFileName).w()

# Interaction

u.cmd("include").arg(ForceFieldFileName).w()

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
u.cmd("run_style").arg(
    "respa 2 2 bond 1 angle 2 dihedral 2 improper 2 pair 2 kspace 2"
).w()

# Grouping

for cmd in [g.group for g in groups if g.group]:
    cmd.w()

# Initial

all.fix("NVE").arg("nve").w()

for cmd in initSet:
    cmd.w()

# Monitor

u.cmd("thermo").arg(1000).w()
u.cmd("thermo_style").arg("multi").w()

for g, interval in zip([all, liq], [10000, 1000]):
    directory = "dumps_{}".format(g.ID)
    u.cmd("shell").arg("mkdir", directory).w()
    g.dump("myDump").arg("custom {inr} {dir}/atom.*.dump {args}".format(
        inr=interval, dir=directory, args="id type xu yu zu vx vy vz"
    )).w()

atomK = all.cmpt("atomK").arg("ke/atom").w()
atomT = u.var("atomT").arg("atom {val}*335.514175".format(val=atomK.ref)).w()
atomVx = u.var("atomicVx").arg("atom vx").w()

for g in [all, liq]:
    chunk = g.cmpt("chunkZ").arg(
        "chunk/atom bin/1d z {orig} {d} bound z {min} {max}".format(
            orig=0.0, d=1.0, min=0.0, max=100.0
        )
    ).w()
    g.fix("distroZ").arg(
        "ave/chunk 1 {dur} {dur} {chunk} {vals} file {file}".format(
            dur=100000, chunk=chunk.ID, vals=" ".join([atomT.ref, atomVx.ref]),
            file="distroZ_{}.dat".format(g.ID)
        )
    ).w()

solVals = [
    u.var("{}Fx".format(g.ID)).arg("equal fcm({},x)".format(g.ID)).w()
    for g in [lBase, lSolid, uBase, uSolid]
]

uBaseFz = u.var("uBaseFz").arg("equal fcm(uBase,z)").w()
lSurfZ, uSurfZ = [
    u.var("{}Z".format(g.ID)).arg("equal xcm({},z)".format(g.ID)).w()
    for g in [lSurf, uSurf]
]

solVals.extend([
    uBaseFz, lSurfZ, uSurfZ,
    u.var("uFz2").arg("equal {v}*{v}".format(v=uBaseFz.ref)).w(),
    u.var("gap").arg("equal {u}-{v}".format(u=uSurfZ.ref, v=lSurfZ.ref)).w()
])

all.fix("SolVals").arg("ave/time 1 {dur} {dur} {vals} file {file}".format(
    dur=1000, vals=" ".join([v.ref for v in solVals]), file="Vals_sol.dat"
)).w()

liqVal = liq.cmpt("temp").arg("temp").w()

all.fix("LiqVals").arg("ave/time 1 {dur} {dur} {vals} file {file}".format(
    dur=1000, vals=liqVal.ref, file="Vals_liq.dat"
)).w()

# Run Heat

u.cmd("log").arg("log.heat append").w()
u.cmd("run").arg((TemperatureStop - TemperatureStart) * StepPerKelvin).w()
u.cmd("write_data").arg("data.{}_heat nocoeff".format(SimulationName)).w()

# Run Stay

u.cmd("log").arg("log.stay append").w()

for cmd in staySet:
    cmd.w()

u.cmd("run").arg(NumSteps).w()
u.cmd("write_data").arg("data.{}_stay nocoeff".format(SimulationName)).w()
