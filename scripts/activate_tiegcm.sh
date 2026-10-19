# Source-only workspace stack; no conda shell initialization.
source /workspace/data/20261016/scripts/activate_orbit.sh
export TIEGCM_STACK=/workspace/data/20261016/.envs/tiegcm
export PATH="$TIEGCM_STACK/bin:$PATH"
export LD_LIBRARY_PATH="$TIEGCM_STACK/lib:${LD_LIBRARY_PATH:-}"
export OMPI_FC="$TIEGCM_STACK/bin/x86_64-conda-linux-gnu-gfortran"
export OMPI_CC="$TIEGCM_STACK/bin/x86_64-conda-linux-gnu-gcc"
export OMPI_CXX="$TIEGCM_STACK/bin/x86_64-conda-linux-gnu-g++"
export OMPI_MCA_orte_tmpdir_base=/workspace/data/20261016/.tmp/mpi
export PRTE_MCA_prte_tmpdir_base=/workspace/data/20261016/.tmp/mpi
export PMIX_MCA_pmix_server_tmpdir=/workspace/data/20261016/.tmp/mpi
export TMPDIR=/workspace/data/20261016/.tmp/mpi
export OMP_NUM_THREADS=1
mkdir -p "$TMPDIR"
