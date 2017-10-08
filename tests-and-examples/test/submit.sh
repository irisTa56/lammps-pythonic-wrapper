#!/bin/bash

#PJM --rsc-list "rscgrp=cx-debug"
#PJM --rsc-list "vnode=1"
#PJM --rsc-list "vnode-core=28"
#PJM --rsc-list "elapse=5:00"
#PJM -P "vn-policy=abs-unpack"
#PJM -N "Deep"
#PJM -S
#PJM -j

mpirun="mpiexec.hydra -np 28"
pyexecutable="$HOME/.pyenv/shims/python"
pytarget="script.py"

source $HOME/.bash_runtime

$mpirun $pyexecutable $pytarget
