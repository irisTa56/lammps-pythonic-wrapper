# This script runs a bulk simulation

from wapylmp import (
  MyLammps,
  get_table_length, get_table_name, compute_kinetic_variance_ratio)

import os
import itertools as it

simulation_name = "T20"
gamma = 20.0

data_file = "./data_files/data.quenched_100ns_scaled"

num_molecules = 125

dump_name = "bead.*.dump"
dump_dir = "dumps"
dump_interval_time = 10000  # [fs]

potential_bond = {  # type => filepath
  1: "./potential_files/bond_length.table"
}

potential_angle = {  # type => filepath
  1: "./potential_files/bond_angle.table"
}

potential_nonbond = {  # (type1, type2) => (filepath, name, cutoff [ang])
  (1, 1): ("./potential_files/non_bond_ll.table", 16.5)
}

dpd_cutoff = 8.1  # [ang]

dpd_parameters = {  # (type1, type2) => (gamma [kcal/mol*fs/ang^2], cutoff [ang])
  (1, 1): (gamma, gamma, dpd_cutoff)
}

random_seed = 2018

time_step = 5.0  # [fs]

respa_setting = (2, 4, "bond", 1, "hybrid", 2, 1)
respa_scale = 4

temperature = 300  # [K]

total_time = 10000  # [fs]
write_data_every_this_time = 10000  # [fs]

num_steps_dump_interval = int(dump_interval_time/time_step)

num_loops = int(total_time/write_data_every_this_time)
num_steps = int(total_time/time_step/num_loops)

#--------------#
# Setup Lammps #
#--------------#

L = MyLammps(name="trans")

L.units("real")

L.atom_style("angle")
L.dimension(3)
L.boundary("p p p")

L.read_data(data_file)

L.special_bonds("lj/coul", 1e-20, 1e-20, 1.0)

L.neigh_modify("delay", 0)
L.comm_modify ("vel", "yes")

L.timestep(time_step)

#------------#
# Potentials #
#------------#

L.bond_style("table", "linear", max(
  get_table_length(v) for v in potential_bond.values()))

for k, v in potential_bond.items():
  L.bond_coeff(k, v, get_table_name(v))

L.angle_style("table", "linear", max(
  get_table_length(v) for v in potential_angle.values()))

for k, v in potential_angle.items():
  L.angle_coeff(k, v, get_table_name(v))

respa_temp = respa_scale*temperature

L.pair_style(
  "hybrid/overlay/tally",
  "table", "linear", max(  # use the maximum cutoff as a global cutoff
    get_table_length(v[0]) for v in potential_nonbond.values()),
  "dpd/trans/tstat", respa_temp, respa_temp, dpd_cutoff, random_seed)

L.pair_modify("pair", "table", "special", "lj", 0.0, 0.0, 1.0)
for k, v in potential_nonbond.items():
  L.pair_coeff(*k, "table", v[0], get_table_name(v[0]), v[1])

L.pair_modify("pair", "dpd/trans/tstat", "special", "lj", 1.0, 1.0, 1.0)
for k, v in dpd_parameters.items():
  L.pair_coeff(*k, "dpd/trans/tstat", *v)

#-------------------#
# Initialize Groups #
#-------------------#

L.run_style("respa", *respa_setting)

L.fix(1, "all", "nve")

#------------------#
# Monitor Settings #
#------------------#

if L.lmp.comm.rank == 0:
  os.makedirs(dump_dir, exist_ok=True)

L.dump(
  1, "all", "custom", num_steps_dump_interval,
  os.path.join(dump_dir, dump_name), "id mol type xu yu zu vx vy vz")

L.thermo(1000)
L.thermo_style("one")
L.thermo_modify("flush", "yes")

ratio_atom, ratio_mol = compute_kinetic_variance_ratio(
  LMP=L, group="all", num_molecules=num_molecules)

L.fix(
  "monitor", "all", "ave/time", 100, 10, 1000,
  "c_thermo_temp", ratio_atom, ratio_mol, "file", "profile.monitor")

# compute/tally

L.compute("pe_pair", "all", "pe", "pair")

L.compute("pe_table", "all", "pe/tally", "all")
L.compute("sum_pe_table", "all", "reduce", "sum", "c_pe_table[*]")
L.pair_modify("pair", "table", "compute/tally", "pe_table")

L.fix(
  "tally1", "all", "ave/time", 100, 10, 1000,
  "c_pe_pair", "c_sum_pe_table[1]", "file", "profile.tally.potential")

#-----#
# Run #
#-----#

for i in range(num_loops):

  L.log("log.run-{}".format(i))

  L.run(num_steps)
  L.write_data("data.{}_run-{}".format(simulation_name, i), "nocoeff")
