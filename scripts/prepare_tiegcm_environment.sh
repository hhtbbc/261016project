#!/usr/bin/env bash
# Workspace-only package solver, no shell initialization or global activation.
set -euo pipefail
ROOT=/workspace/data/20261016
source "$ROOT/scripts/activate_orbit.sh"
export MAMBA_ROOT_PREFIX="$ROOT/.local/mamba"
export CONDA_PKGS_DIRS="$ROOT/.cache/conda/pkgs"
export CONDA_ENVS_PATH="$ROOT/.envs"
export PYTHONNOUSERSITE=1
case "$(realpath -m "$MAMBA_ROOT_PREFIX")" in "$ROOT"/*) ;; *) exit 1;; esac
mkdir -p "$MAMBA_ROOT_PREFIX" "$CONDA_PKGS_DIRS" "$CONDA_ENVS_PATH"
mkdir -p "$ROOT/.envs/tiegcm/conda-meta"
if [ ! -f "$ROOT/.envs/tiegcm/conda-meta/history" ]; then touch "$ROOT/.envs/tiegcm/conda-meta/history"; fi
# Use install, never create: create writes a HOME-level environments registry.
"$ROOT/.local/bin/micromamba" --no-rc install --root-prefix "$MAMBA_ROOT_PREFIX" \
 --prefix "$ROOT/.envs/tiegcm" --override-channels --channel conda-forge \
 --strict-channel-priority --dry-run --json \
 'gfortran_linux-64=12' 'gxx_linux-64=12' 'esmf=8.6.*=mpi_openmpi*' netcdf-fortran openmpi \
 > "$ROOT/logs/tiegcm_stack_solve.json" 2> "$ROOT/logs/tiegcm_stack_solve.stderr"
