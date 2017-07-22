import itertools as it
from lammps_wrapper_interface import Manager

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
        "uFree": [9, 11, 13, 15, 17],
        "liq": None
    },
    "union": {
        "lSolid": ["lBase", "lBath", "lFree"],
        "uSolid": ["uBase", "uBath", "uFree"]
    },
})

# Parameters

SimulationName = "N60onDeep_confine"

DataFileName1 = "../Dia001O_Deep/data.Solid_lower"
DataFileName2 = "../Dia001O_Deep/data.Solid_upper"
ForceFieldFileName = "../Dia001O_Deep/forcefield.ZonDia001O"
MoleculeFileName = "../Dia001O_Deep/molecule.Z1800"

RandomSeed = 2017
Temperature = 300
NumMolecules = 60
DepositInterval = 10000
NormalForce = -0.0455 # 50 MPa
NumSteps_Eq1 = 1000000
NumSteps_Eq2 = 2000000

MassList = [
    12.011, 15.999, 18.998, 12.011, 12.011,
    12.011, 12.011, 12.011, 12.011, 12.011,
    12.011, 12.011, 12.011, 15.999, 15.999, 15.999, 15.999
]

Clusters = {
    "lower": [4, 6, 8, 10, 12, 14, 16],
    "upper": [5, 7, 9, 11, 13, 15, 17]
}

# Advance setting

readData = m.Universe.addCmd("read_data", DataFileName1)
addData = m.Universe.addCmd("read_data", DataFileName2, "add append")

setMass = [
    m.Universe.addCmd("mass", "{type:2d} {mass}".format(type=i+1, mass=mass))
    for i, mass in enumerate(MassList)
]

readForceField = m.Universe.addCmd("include", ForceFieldFileName)

excludePair = {key: [
    m.Universe.addCmd("neigh_modify", "exclude type {i:2d} {j:2d}".format(
        i=pair[0], j=pair[1]
    )) for pair in list(it.combinations_with_replacement(val, 2))
] for key, val in Clusters.items()}

addMolecule = m.Universe.addMol("Z1800", MoleculeFileName)

lBaseSet = [
    m.Groups["lBase"].addFix("freeze", "setforce 0.0 0.0 0.0"),
    m.Groups["lBase"].addCmd("velocity", "set 0.0 0.0 0.0")
]

uBaseSet = [
    m.Groups["uBase"].addFix(
        "load", "aveforce NULL NULL {fz}".format(fz=NormalForce)
    ),
    m.Groups["uBase"].addFix("freeZ", "setforce 0.0 0.0 NULL"),
    m.Groups["uBase"].addCmd("velocity", "set 0.0 0.0 0.0")
]

for Set, groups in zip([lBaseSet, uBaseSet],
                       [["lBath", "lFree"], ["uBath", "uFree"]]):
    for group in groups:
        Set.append(m.Groups[group].addCmd(
            "velocity", "create {temp} {seed} {args}".format(
                temp=Temperature,
                seed=RandomSeed,
                args="mom yes rot yes dist gaussian"
            )
        ))

for Set, group in zip([lBaseSet, uBaseSet], ["lBath", "uBath"]):
    Set.append(m.Groups[group].addCmpt("noBiasTemp", "temp/com"))
    Set.append(m.Groups[group].addFix(
        "thermostat", "langevin {temp} {temp} {damp} {seed}".format(
            temp=Temperature,
            damp=100,
            seed=RandomSeed
        )
    ))
    Set.append(m.Universe.addCmd("fix_modify", "{fix} temp {cmpt}".format(
        fix=Set[-1].ID, cmpt=Set[-2].ID
    )))

# System

m.addSetting("System")

m.System.processors = "* * 1"
m.System.units = "real"
m.System.atom_style = "full"
m.System.dimension = 3
m.System.boundary = "p p f"

m.System.apply("Read data.* file", readData)

m.System.apply("Set masses", *setMass)

# Interaction

m.addSetting("Interaction")

m.Interaction.apply("Read forcefield.* file", readForceField)

m.Interaction.dielectric = 1.0
m.Interaction.pair_modify = "shift yes mix sixthpower"
m.Interaction.special_bonds = "lj/coul 0.0 0.0 1.0"
m.Interaction.neighbor = "2.0 bin"
m.Interaction.neigh_modify = "delay 0 one 5000"
m.Interaction.kspace_style = "pppm 1e-5"
m.Interaction.kspace_modify = "slab 3.0"

for key, val in excludePair.items():
    m.Interaction.apply(
        "Exclude pair interaction between {cluster} solid atoms".format(
            cluster=key
        ), *val
    )

# Dynamics

m.addSetting("Dynamics")

m.Dynamics.timestep = 1.0
m.Dynamics.run_style = \
    "respa 2 2 bond 1 angle 2 dihedral 2 improper 2 pair 2 kspace 2"

# Grouping

m.addSetting("Grouping")

m.Grouping.apply("Create groups", *[g.group for g in m.Groups.values()])

# Initial

m.addSetting("Initial")

m.Initial.apply("Apply NVE", m.Groups["all"].addFix("NVE", "nve"))

m.Initial.apply("Initial settings for lower solid atoms", *lBaseSet)

# Monitor

m.addSetting("Monitor")

m.Monitor.thermo = 1000
m.Monitor.thermo_style = "multi"

for group, interval in zip(["all", "liq"], [10000, 1000]):
    directory = "dumps_{group}".format(group=group)
    m.Monitor.apply(
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
m.Monitor.apply("Calculate temperature of each atom", tmpKe, tmpTemp)

for group in ["all", "liq"]:
    chunk = m.Groups[group].addCmpt(
        "chunkZ",
        "chunk/atom bin/1d z {origin} {delta} bound z {minz} {maxz}".format(
            origin=0.0, delta=1.0, minz=0.0, maxz=100.0
        )
    )
    m.Monitor.apply(
        "Output temperature distribution along z axis", chunk,
        m.Groups[group].addFix(
            "distroZ",
            "ave/chunk 1 {duration} {duration} {chunk} {vals} file {file}".format(
                duration=100000, chunk=chunk.ID, vals=m.getValStr(tmpTemp),
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
m.Monitor.apply("Values associated with solid atoms", *solidVals)

m.Monitor.apply(
    "Output values associated with solid atoms", m.Groups["all"].addFix(
        "SolVals", "ave/time 1 {duration} {duration} {vals} file {file}".format(
            duration=1000, vals=m.getValStr(*solidVals), file="solidVals.dat"
        )
    )
)

liqVal = m.Groups["liq"].addCmpt("temp", "temp")
m.Monitor.apply("Values associated with liquid atoms", liqVal)

m.Monitor.apply(
    "Outpt values associated with liquid atoms", m.Groups["all"].addFix(
        "LiqVals", "ave/time 1 {duration} {duration} {vals} file {file}".format(
            duration=1000, vals=m.getValStr(liqVal), file="liqVals.dat"
        )
    )
)

# Run Deposition

m.addSetting("Deposition")

m.Deposition.log = "log.deposition append"

region = m.Universe.addReg(
    "depositSpace", "block EDGE EDGE EDGE EDGE {minz} {maxz}".format(
        minz=60.0, maxz=80.0
    )
)
m.Deposition.apply(
    "Put molecules to a specified region", addMolecule, region,
    m.Groups["liq"].addFix(
        "deposit{mol}".format(mol=addMolecule.ID),
        "deposit {num} 0 {interval} {seed} region {reg} vz {velz} {velz} mol {mol}".format(
            num=NumMolecules, interval=DepositInterval, seed=RandomSeed,
            reg=region.ID, velz=-0.005, mol=addMolecule.ID
        )
    )
)

temp = m.Groups["liq"].addCmpt("xyTemp", "temp/partial 1 1 0")
langevin = m.Groups["liq"].addFix(
    "langevin", "langevin {temp} {temp} {damp} {seed}".format(
        temp=Temperature, damp=100, seed=RandomSeed
    )
)
m.Deposition.apply(
    "Apply Langevin thermostat to X-, Y-directional temperature of liquid",
    temp, langevin, m.Universe.addCmd("fix_modify", "{fix} temp {cmpt}".format(
        fix=langevin.ID, cmpt=temp.ID
    ))
)

m.Deposition.apply(
    "Run to deposite molecules",
    m.Universe.addCmd("run", NumMolecules*DepositInterval), langevin.unfix
)

m.Deposition.write_data = "data.{}_deposition nocoeff".format(SimulationName)

# Run First Equilibration

m.addSetting("FirstEq")

m.FirstEq.log = "log.eq1 append"
m.FirstEq.run = NumSteps_Eq1
m.FirstEq.write_data = "data.{}_eq1 nocoeff".format(SimulationName)

# Add Upper Solid Plate

m.addSetting("AddUpper")

m.AddUpper.apply("Add upper solid atoms", addData)

m.AddUpper.apply(
    "Add atoms to groups in the upper solid plate",
    *[m.Groups[g].group for g in ["uBase", "uBath", "uSurf", "uFree", "uSolid"]]
)

m.AddUpper.apply("Initial settings for upper solid atoms", *uBaseSet)

# Run Second Equilibration

m.addSetting("SecondEq")

m.SecondEq.log = "log.eq2 append"
m.SecondEq.run = NumSteps_Eq2
m.SecondEq.write_data = "data.{}_eq2 nocoeff".format(SimulationName)

m.outputAll()
