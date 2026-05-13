#!/bin/bash
# Sequential haiku → sonnet runner. Both share the Claude account, so
# parallelizing them just doubles the rate-limit pressure. The pipeline's
# _sleep_through_claude_limit (deep/llm.py) handles 5-hour-window resets
# with up to 6×60min retries per blocked call.
set -e
cd "$(dirname "$0")/.."

export CLAUDE_CODE_KEY=cli
export DEEPTEST_RESULTS_DIR=results_v2
TS=$(date +%Y%m%d_%H%M%S)

echo "[$(date +%H:%M:%S)] HAIKU_START"
python3 -u -m bugtest benchmark_v2_haiku_100.yaml \
    > logs/v2_haiku_100_${TS}.log 2>&1 || echo "[$(date +%H:%M:%S)] HAIKU_EXIT_NONZERO"
echo "[$(date +%H:%M:%S)] HAIKU_END"

echo "[$(date +%H:%M:%S)] SONNET_START"
python3 -u -m bugtest benchmark_v2_sonnet_100.yaml \
    > logs/v2_sonnet_100_${TS}.log 2>&1 || echo "[$(date +%H:%M:%S)] SONNET_EXIT_NONZERO"
echo "[$(date +%H:%M:%S)] SONNET_END"
