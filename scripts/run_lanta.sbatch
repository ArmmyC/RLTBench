#!/usr/bin/env bash
#SBATCH --job-name=rtlbench
#SBATCH --partition=compute
#SBATCH --account=zz992005
#SBATCH --qos=zz992005
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=logs/rtlbench-%j.out
#SBATCH --error=logs/rtlbench-%j.err

set -euo pipefail

ROOT=${ROOT:-/project/zz992000-zdevb/zz992005/ub127/SiliconCraft/benchmark}
ENV_PREFIX=${ENV_PREFIX:-$ROOT/.conda-env}
CONFIG=${CONFIG:-$ROOT/configs/verilogeval.yaml}

cd "$ROOT"
mkdir -p logs

if [ -z "${OPENAI_BASE_URL:-}" ]; then
  VLLM_JOB_NAME=${VLLM_JOB_NAME:-vllm-model}
  VLLM_NODE=$(squeue -u "$USER" -h -n "$VLLM_JOB_NAME" -t R -o "%N" | awk 'NF {print $1; exit}')
  if [ -z "$VLLM_NODE" ]; then
    echo "No running $VLLM_JOB_NAME job found; set OPENAI_BASE_URL explicitly." >&2
    exit 2
  fi
  export OPENAI_BASE_URL="http://$VLLM_NODE:${VLLM_PORT:-8000}/v1"
fi

exec "$ENV_PREFIX/bin/rtlbench" --config "$CONFIG" "$@"
