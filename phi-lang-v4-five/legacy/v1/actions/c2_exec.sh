#!/bin/bash
# c2_exec.sh — Execute system command (Tier 2 — needs binary gate approval first)
CMD="$2"
echo "φack:id=exec,n=${1:-Oracle},cmd=$CMD,status=routed_to_shell"
exec $CMD 2>&1 || echo "φerr:reason=exec_failed"

