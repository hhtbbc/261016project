#!/usr/bin/env bash
# Do not use `micromamba create`: it registers environments outside the workspace.
# Reviewed mamba 2.9.0 install.cpp: install into an existing prefix does not call
# create_target_directory/register_env. Package post-link scripts audited first.
set -euo pipefail
ROOT=/workspace/data/20261016
source "$ROOT/scripts/activate_orbit.sh"
export MAMBA_ROOT_PREFIX="$ROOT/.local/mamba"
export CONDA_PKGS_DIRS="$ROOT/.cache/conda/pkgs"
export CONDA_ENVS_PATH="$ROOT/.envs"
PREFIX_PATH="$ROOT/.envs/tiegcm"
for target in "$MAMBA_ROOT_PREFIX" "$CONDA_PKGS_DIRS" "$PREFIX_PATH"; do
 case "$(realpath -m "$target")" in "$ROOT"/*) ;; *) exit 1;; esac
done
mkdir -p "$PREFIX_PATH/conda-meta"
if [ ! -f "$PREFIX_PATH/conda-meta/history" ]; then touch "$PREFIX_PATH/conda-meta/history"; fi
"$ROOT/.local/bin/micromamba" --no-rc install --root-prefix "$MAMBA_ROOT_PREFIX" \
 --prefix "$PREFIX_PATH" --file "$ROOT/configs/tiegcm-stack-explicit.txt" --offline -y
