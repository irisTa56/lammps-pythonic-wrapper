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

m = LammpsManager()
univ = m.getUniverse()

All, lBase, lBath, lSurf, lFree, uBase, uBath, uSurf, uFree, \
lSolid, uSolid, liq = m.createGroups({
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
        "liq": range(1, NumMolecules+1)
    }
})

# Advance setting

readData = univ.cmd("read_data", DataFileName)
readForceField = univ.cmd("include", ForceFieldFileName)

excludePair = {key: [univ.cmd(
    "neigh_modify", "exclude type {:2d} {:2d}".format(pair[0], pair[1])
) for pair in list(it.combinations_with_replacement(
    [2*i+n+4 for i in range(7)], 2
))] for n, key in enumerate(["lower", "upper"])}

lSolidSet = [lBase.fix("freeze", "setforce 0.0 0.0 0.0")]

uSolidSet = [
    uBase.fix("load", "aveforce NULL NULL {fz}".format(fz=NormalForce)),
    uBase.fix("freeZ", "setforce 0.0 0.0 NULL"),
    uBase.cmpt("tempZ", "temp/partial 0 0 1"),
    uBase.fix("damper", "langevin 0 0 {damp} {seed}".format(
        damp=100, seed=RandomSeed
    ))
]

uSolidSet.append(univ.cmd("fix_modify", "{fix} temp {cmpt}".format(
    fix=uSolidSet[-1].ID, cmpt=uSolidSet[-2].ID
)))

for s, g in zip([lSolidSet, uSolidSet], [lBath, uBath]):
    s.append(g.cmpt("noBiasTemp", "temp/com"))
    s.append(g.fix(
        "heat", "langevin {temp1} {temp2} {damp} {seed}".format(
            temp1=TemperatureStart, temp2=TemperatureStop,
            damp=100, seed=RandomSeed
        )
    ))
    s.append(univ.cmd("fix_modify", "{fix} temp {cmpt}".format(
        fix=s[-1].ID, cmpt=s[-2].ID
    )))

staySet = []
for g in [lBath, uBath]:
    staySet.append(g.fixes["heat"].unfix)
    staySet.append(g.fix(
        "thermostat", "langevin {temp} {temp} {damp} {seed}".format(
            temp=TemperatureStop, damp=100, seed=RandomSeed
        )
    ))
    staySet.append(univ.cmd("fix_modify", "{fix} temp {cmpt}".format(
        fix=staySet[-1].ID, cmpt=g.cmpts["noBiasTemp"].ID
    )))

# System

sy = m.addCommandAcceptor("System")

sy.processors = "* * 1"
sy.units = "real"
sy.atom_style = "full"
sy.dimension = 3
sy.boundary = "p p f"

sy.apply("Read data.* file", readData)

# Interaction

ia = m.addCommandAcceptor("Interaction")

ia.apply("Read forcefield.* file", readForceField)

ia.dielectric = 1.0
ia.pair_modify = "shift yes mix sixthpower"
ia.special_bonds = "lj/coul 0.0 0.0 1.0"
ia.neighbor = "2.0 bin"
ia.neigh_modify = "delay 0 one 5000"
ia.kspace_style = "pppm 1e-5"
ia.kspace_modify = "slab 3.0"

for key, val in excludePair.items():
    ia.apply("Exclude pair interaction between solid atoms", *val)

# Dynamics

dy = m.addCommandAcceptor("Dynamics")

dy.timestep = 1.0
dy.run_style = "respa 2 2 bond 1 angle 2 dihedral 2 improper 2 pair 2 kspace 2"

# Grouping

m.addCommandAcceptor("Grouping").apply(
    "Create groups", *[g.group for g in m.Groups.values()]
)

# Initial

ini = m.addCommandAcceptor("Initial")

ini.apply("Apply NVE", All.fix("NVE", "nve"))
ini.apply("Initial settings for lower solid atoms", *lSolidSet)
ini.apply("Initial settings for upper solid atoms", *uSolidSet)

# Monitor

mon = m.addCommandAcceptor("Monitor")

mon.thermo = 1000
mon.thermo_style = "multi"

for g, interval in zip([All, liq], [10000, 1000]):
    directory = "dumps_{}".format(g.ID)
    mon.apply(
        "Set dump",
        univ.cmd("shell", "mkdir {dir}".format(dir=directory)),
        g.dump("myDump", "custom {inr} {dir}/atom.*.dump {args}".format(
            inr=interval, dir=directory, args="id type xu yu zu vx vy vz"
        ))
    )

tmpKe = All.cmpt("atomicK", "ke/atom")
tmpTemp = univ.var("atomicT", "atom {val}*335.514175".format(
    val=m.getValStr(tmpKe)
))
tmpVx = univ.var("atomicVx", "atom vx")
mon.apply("Calculate temperature of each atom", tmpKe, tmpTemp, tmpVx)

for g in [All, liq]:
    chunk = g.cmpt(
        "chunkZ",
        "chunk/atom bin/1d z {origin} {delta} bound z {minz} {maxz}".format(
            origin=0.0, delta=1.0, minz=0.0, maxz=100.0
        )
    )
    mon.apply(
        "Output temperature distribution along z axis", chunk,
        g.fix(
            "distroZ",
            "ave/chunk 1 {dur} {dur} {chunk} {vals} file {file}".format(
                dur=100000, chunk=chunk.ID, vals=m.getValStr(tmpTemp, tmpVx),
                file="distroZ_{}.dat".format(g.ID)
            )
        )
    )

solidVals = [univ.var(
    "{}Fx".format(g.ID), "equal fcm({},x)".format(g.ID)
) for g in [lBase, lSolid, uBase, uSolid]]
solidVals.append(univ.var("uBaseFz", "equal fcm(uBase,z)"))
solidVals.extend([univ.var(
    "{}Z".format(g.ID), "equal xcm({},z)".format(g.ID)
) for g in [lSurf, uSurf]])
solidVals.append(univ.var("uBaseFz2", "equal {val}*{val}".format(
    val=m.getValStr("uBaseFz")
)))
solidVals.append(univ.var("gap", "equal {vals[0]}-{vals[1]}".format(
    vals=m.getValStr("uSurfZ", "lSurfZ", Join=False)
)))
mon.apply("Values associated with solid atoms", *solidVals)

mon.apply("Output values associated with solid atoms", All.fix(
    "SolVals", "ave/time 1 {dur} {dur} {vals} file {file}".format(
        dur=1000, vals=m.getValStr(*solidVals), file="solidVals.dat"
    )
))

liqVal = liq.cmpt("temp", "temp")
mon.apply("Values associated with liquid atoms", liqVal)

mon.apply("Outpt values associated with liquid atoms", All.fix(
    "LiqVals", "ave/time 1 {dur} {dur} {vals} file {file}".format(
        dur=1000, vals=m.getValStr(liqVal), file="liqVals.dat"
    )
))

# Run Heat

heat = m.addCommandAcceptor("Heat")

heat.log = "log.heat append"
heat.run = (TemperatureStop - TemperatureStart) * StepPerKelvin
heat.write_data = "data.{}_heat nocoeff".format(SimulationName)

# Run Stay

stay = m.addCommandAcceptor("Stay")

stay.log = "log.stay append"
stay.apply("Stop heating and apply thermostat.", *staySet)
stay.run = NumSteps
stay.write_data = "data.{}_stay nocoeff".format(SimulationName)

m.outputAll(filename="in.heat")
