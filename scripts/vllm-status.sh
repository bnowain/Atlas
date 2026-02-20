#!/usr/bin/env bash
# Check status of vLLM backends

echo "vLLM Backend Status"
echo "==================="

check() {
  local name=$1 port=$2
  if curl -sf "http://localhost:${port}/v1/models" > /dev/null 2>&1; then
    model=$(curl -sf "http://localhost:${port}/v1/models" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "unknown")
    echo "  [+] $name (port $port) — $model"
  else
    echo "  [-] $name (port $port) — offline"
  fi
}

check "atlas-fast"    8100
check "atlas-quality" 8101
check "atlas-code"    8102
