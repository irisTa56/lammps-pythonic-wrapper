def get_table_name(path):
  with open(path, "r") as f:
    return (f.readlines()[2].strip())

def get_table_length(path):
  with open(path, "r") as f:
    return int(f.readlines()[3].split()[1])

def compute_kinetic_variance_ratio(
  LMP, group="all", num_molecules=0,
  name_atom="_ratio_atom", name_mol="_ratio_mol"):
  """
  Compute <K^2>/<K>^2 of atoms and molecules, where K is kinetic energy
  and <*> stands for ensemble average. For equilibrium gas, this value
  approaches 5/3.

  @return
    Name(s) of variable (in format of 'v_*') where computed value is
    assigned to. If `num_molecules == 0` holds, only the name for atoms
    will be returned.
  """

  LMP.compute("K_atom", group, "ke/atom")
  LMP.compute("K2ave_atom", group, "reduce", "avesq", "c_K_atom")
  LMP.compute("Kave_atom", group, "reduce", "ave", "c_K_atom")
  LMP.variable("Kave2_atom", "equal", "c_Kave_atom*c_Kave_atom")
  LMP.variable(name_atom, "equal", "c_K2ave_atom/v_Kave2_atom")

  if 0 < num_molecules:

    LMP.compute("molchunk", group, "chunk/atom", "molecule")
    LMP.compute("K_mol", group, "temp/chunk", "molchunk", "kecom")

    LMP.variable("K_0_mol", "equal", "0.0")
    LMP.variable("K2_0_mol", "equal", "0.0")

    for i in range(num_molecules):

      LMP.variable(
        "K_{}_mol".format(i+1), "equal",
        "v_K_{}_mol+c_K_mol[{}][1]".format(i, i+1))
      LMP.variable(
        "K2_{}_mol".format(i+1), "equal",
        "v_K2_{0}_mol+c_K_mol[{1}][1]*c_K_mol[{1}][1]".format(i, i+1))

    LMP.variable(
      "Kave_mol", "equal",
      "v_K_{}_mol*{}".format(num_molecules, 1/num_molecules))
    LMP.variable(
      "K2ave_mol", "equal",
      "v_K2_{}_mol*{}".format(num_molecules, 1/num_molecules))
    LMP.variable("Kave2_mol", "equal", "v_Kave_mol*v_Kave_mol")
    LMP.variable(name_mol, "equal", "v_K2ave_mol/v_Kave2_mol")

  if 0 < num_molecules:
    return ("v_{}".format(name_atom), "v_{}".format(name_mol))
  else:
    return "v_{}".format(name_atom)
