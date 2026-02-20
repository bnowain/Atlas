#!/usr/bin/env bash
# Start three vLLM backends in tmux sessions (run from WSL2)

set -euo pipefail

echo "Starting vLLM backends..."

# atlas-fast: Qwen2.5-7B
tmux new-session -d -s atlas-fast \
  "vllm serve Qwen/Qwen2.5-7B-Instruct \
    --port 8100 \
    --host 0.0.0.0 \
    --max-model-len 32768 \
    2>&1 | tee /tmp/vllm-fast.log"

echo "  [+] atlas-fast (Qwen2.5-7B) on port 8100"

# atlas-quality: Qwen2.5-72B-AWQ
tmux new-session -d -s atlas-quality \
  "vllm serve Qwen/Qwen2.5-72B-Instruct-AWQ \
    --port 8101 \
    --host 0.0.0.0 \
    --max-model-len 16384 \
    --quantization awq \
    2>&1 | tee /tmp/vllm-quality.log"

echo "  [+] atlas-quality (Qwen2.5-72B-AWQ) on port 8101"

# atlas-code: DeepSeek-Coder-V2-Lite
tmux new-session -d -s atlas-code \
  "vllm serve deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct \
    --port 8102 \
    --host 0.0.0.0 \
    --max-model-len 16384 \
    2>&1 | tee /tmp/vllm-code.log"

echo "  [+] atlas-code (DeepSeek-Coder-V2-Lite) on port 8102"
echo ""
echo "All backends started. Use 'tmux ls' to see sessions."
echo "Logs: /tmp/vllm-{fast,quality,code}.log"
