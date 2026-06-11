#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/project/zz992000-zdevb/zz992005/ub127/SiliconCraft/benchmark}
ENV_PREFIX=${ENV_PREFIX:-$ROOT/.conda-env}
export TMPDIR=${TMPDIR:-$ROOT/.tmp}
mkdir -p "$TMPDIR"

if command -v mamba >/dev/null 2>&1; then
  SOLVER=mamba
else
  SOLVER=conda
fi

if [ ! -x "$ENV_PREFIX/bin/python" ]; then
  "$SOLVER" create -y -p "$ENV_PREFIX" -c conda-forge python=3.11 iverilog pip
fi

if [ ! -x "$ENV_PREFIX/bin/python" ]; then
  echo "Environment creation failed: $ENV_PREFIX/bin/python is missing" >&2
  exit 1
fi

"$ENV_PREFIX/bin/python" -m pip install -e "$ROOT[dev]"
echo "Environment ready: $ENV_PREFIX"
