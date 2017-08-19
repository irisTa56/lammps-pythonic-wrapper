import itertools as it
from lammps_pythonic_wrapper import Manager

# Parameters

SimulationName = "N72onH1_Heat300K"

DataFileName = "../DATA/data.N72onH1_confined"
ForceFieldFileName = "../DATA/forcefield.ZonH1"

RandomSeed = 2017
NumMolecules = 72
TemperatureStart = 300
TemperatureStop = 500
StepPerKelvin = 1000
NormalForce = -0.0455 # 50 MPa
NumSteps = 2000000

Clusters = {
    "lower": [4, 6, 8, 10, 12, 14, 16],
    "upper": [5, 7, 9, 11, 13, 15, 17]
}

# Create Manager

m = Manager()

m.createGroups({
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

readData = m.Universe.addCmd("read_data", DataFileName)

readForceField = m.Universe.addCmd("include", ForceFieldFileName)

excludePair = {key: [
    m.Universe.addCmd("neigh_modify", "exclude type {i:2d} {j:2d}".format(
        i=pair[0], j=pair[1]
    )) for pair in list(it.combinations_with_replacement(val, 2))
] for key, val in Clusters.items()}

lSolidSet = [
    m.Groups["lBase"].addFix("freeze", "setforce 0.0 0.0 0.0")
]

uSolidSet = [
    m.Groups["uBase"].addFix(
        "load", "aveforce NULL NULL {fz}".format(fz=NormalForce)
    ),
    m.Groups["uBase"].addFix("freeZ", "setforce 0.0 0.0 NULL"),
    m.Groups["uBase"].addCmpt("tempZ", "temp/partial 0 0 1"),
    m.Groups["uBase"].addFix(
        "damper", "langevin 0 0 {damp} {seed}".format(
            damp=100, seed=RandomSeed
        )
    )
]
uSolidSet.append(m.Universe.addCmd("fix_modify", "{fix} temp {cmpt}".format(
    fix=uSolidSet[-1].ID, cmpt=uSolidSet[-2].ID
)))

for Set, group in zip([lSolidSet, uSolidSet], ["lBath", "uBath"]):
    Set.append(m.Groups[group].addCmpt("noBiasTemp", "temp/com"))
    Set.append(m.Groups[group].addFix(
        "heat", "langevin {temp1} {temp2} {damp} {seed}".format(
            temp1=TemperatureStart, temp2=TemperatureStop,
            damp=100, seed=RandomSeed
        )
    ))
    Set.append(m.Universe.addCmd("fix_modify", "{fix} temp {cmpt}".format(
        fix=Set[-1].ID, cmpt=Set[-2].ID
    )))

staySet = []
for group in ["lBath", "uBath"]:
    staySet.append(m.Groups[group].fixes["heat"].unfix)
    staySet.append(m.Groups[group].addFix(
        "thermostat", "langevin {temp} {temp} {damp} {seed}".format(
            temp=TemperatureStop, damp=100, seed=RandomSeed
        )
    ))
    staySet.append(m.Universe.addCmd("fix_modify", "{fix} temp {cmpt}".format(
        fix=staySet[-1].ID, cmpt=m.Groups[group].computes["noBiasTemp"].ID
    )))



# System

sy = m.addSetting("System")

sy.processors = "* * 1"
sy.units = "real"
sy.atom_style = "full"
sy.dimension = 3
sy.boundary = "p p f"

sy.apply("Read data.* file", readData)

# Interaction

ia = m.addSetting("Interaction")

ia.apply("Read forcefield.* file", readForceField)

ia.dielectric = 1.0
ia.pair_modify = "shift yes mix sixthpower"
ia.special_bonds = "lj/coul 0.0 0.0 1.0"
ia.neighbor = "2.0 bin"
ia.neigh_modify = "delay 0 one 5000"
ia.kspace_style = "pppm 1e-5"
ia.kspace_modify = "slab 3.0"

for key, val in excludePair.items():
    ia.apply("Exclude pair interaction between {cluster} solid atoms".format(
        cluster=key
    ), *val)

# Dynamics

dy = m.addSetting("Dynamics")

dy.timestep = 1.0
dy.run_style = \
    "respa 2 2 bond 1 angle 2 dihedral 2 improper 2 pair 2 kspace 2"

# Grouping

m.addSetting("Grouping").apply(
    "Create groups", *[g.group for g in m.Groups.values()]
)

# Initial

ini = m.addSetting("Initial")

ini.apply("Apply NVE", m.Groups["all"].addFix("NVE", "nve"))
ini.apply("Initial settings for lower solid atoms", *lSolidSet)
ini.apply("Initial settings for upper solid atoms", *uSolidSet)

# Monitor

mon = m.addSetting("Monitor")

mon.thermo = 1000
mon.thermo_style = "multi"

for group, interval in zip(["all", "liq"], [10000, 1000]):
    directory = "dumps_{group}".format(group=group)
    mon.apply(
        "Set dump",
        m.Universe.addCmd("shell", "mkdir {dir}".format(dir=directory)),
        m.Groups[group].addDump(
            "myDump", "custom {interval} {dir}/atom.*.dump {args}".format(
                interval=interval, dir=directory, args="id type xu yu zu vx vy vz"
            )
        )
    )

tmpKe = m.Groups["all"].addCmpt("atomicK", "ke/atom")
tmpTemp = m.Universe.addVar("atomicT", "atom {val}*335.514175".format(
    val=m.getValStr(tmpKe)
))
tmpVx = m.Universe.addVar("atomicVx", "atom vx")
mon.apply("Calculate temperature of each atom", tmpKe, tmpTemp, tmpVx)

for group in ["all", "liq"]:
    chunk = m.Groups[group].addCmpt(
        "chunkZ",
        "chunk/atom bin/1d z {origin} {delta} bound z {minz} {maxz}".format(
            origin=0.0, delta=1.0, minz=0.0, maxz=100.0
        )
    )
    mon.apply(
        "Output temperature distribution along z axis", chunk,
        m.Groups[group].addFix(
            "distroZ",
            "ave/chunk 1 {duration} {duration} {chunk} {vals} file {file}".format(
                duration=100000, chunk=chunk.ID,
                vals=m.getValStr(tmpTemp, tmpVx),
                file="distroZ_{group}.dat".format(group=group)
            )
        )
    )

solidVals = [m.Universe.addVar(
    "{group}Fx".format(group=group), "equal fcm({group},x)".format(group=group)
) for group in ["lBase", "lSolid", "uBase", "uSolid"]]
solidVals.append(m.Universe.addVar("uBaseFz", "equal fcm(uBase,z)"))
solidVals.extend([m.Universe.addVar(
    "{group}Z".format(group=group), "equal xcm({group},z)".format(group=group)
) for group in ["lSurf", "uSurf"]])
solidVals.append(m.Universe.addVar("uBaseFz2", "equal {val}*{val}".format(
    val=m.getValStr("uBaseFz")
)))
solidVals.append(m.Universe.addVar("gap", "equal {vals[0]}-{vals[1]}".format(
    vals=m.getValStr("uSurfZ", "lSurfZ", Join=False)
)))
mon.apply("Values associated with solid atoms", *solidVals)

mon.apply(
    "Output values associated with solid atoms", m.Groups["all"].addFix(
        "SolVals", "ave/time 1 {duration} {duration} {vals} file {file}".format(
            duration=1000, vals=m.getValStr(*solidVals), file="solidVals.dat"
        )
    )
)

liqVal = m.Groups["liq"].addCmpt("temp", "temp")
mon.apply("Values associated with liquid atoms", liqVal)

mon.apply(
    "Outpt values associated with liquid atoms", m.Groups["all"].addFix(
        "LiqVals", "ave/time 1 {duration} {duration} {vals} file {file}".format(
            duration=1000, vals=m.getValStr(liqVal), file="liqVals.dat"
        )
    )
)

# Run Heat

heat = m.addSetting("Heat")

heat.log = "log.heat append"

heat.run = (TemperatureStop - TemperatureStart) * StepPerKelvin
heat.write_data = "data.{}_heat nocoeff".format(SimulationName)

m.outputAll(filename="in.heat")

# Run Stay

stay = m.addSetting("Stay")

stay.log = "log.stay append"

stay.apply(
    "Stop heating and apply thermostat of a constant temperature.",
    *staySet
)

stay.run = NumSteps
stay.write_data = "data.{}_stay nocoeff".format(SimulationName)

m.outputAll(filename="in.heat")
