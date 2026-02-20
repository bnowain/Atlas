#!/usr/bin/env bash
# Stop all vLLM tmux sessions

echo "Stopping vLLM backends..."

for session in atlas-fast atlas-quality atlas-code; do
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux kill-session -t "$session"
    echo "  [-] Stopped $session"
  else
    echo "  [ ] $session not running"
  fi
done

echo "Done."
