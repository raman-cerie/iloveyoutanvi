#!/bin/bash
# c0_ping.sh — Respond to φping with node status (cross-platform)
# macOS + Linux compatible. Zero LLM.

NODE_NAME="${1:-Oracle}"

# Cross-platform uptime
if [[ $(uname) == "Darwin" ]]; then
    # macOS — bash 3.x, no 'uptime -p'
    UPTIME=$(uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}')
else
    UPTIME=$(uptime -p 2>/dev/null | sed 's/up //' || uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}')
fi

# Cross-platform load
LOAD=$(uptime | awk -F'load average:|load averages:' '{print $2}' | xargs)

# Cross-platform memory
if [[ $(uname) == "Darwin" ]]; then
    PAGE_SIZE=$(vm_stat | awk '/page size/ {print $NF}')
    FREE=$(vm_stat | awk '/Pages free/ {gsub(/\./,""); print $NF}')
    USED=$(vm_stat | awk '/Pages active/ {gsub(/\./,""); print $NF}')
    MEM_USED=$(( ($USED * $PAGE_SIZE) / 1048576 ))
    MEM_TOTAL=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1048576)}')
    MEM="${MEM_USED}/${MEM_TOTAL}Mi"
else
    MEM_USED=$(free -m 2>/dev/null | awk '/Mem:/ {print $3}')
    MEM_TOTAL=$(free -m 2>/dev/null | awk '/Mem:/ {print $2}')
    MEM="${MEM_USED}Mi/${MEM_TOTAL}Mi"
fi

GW_STATUS="${GW_PORT:-unknown}"

echo "φpong:n=$NODE_NAME,up=$UPTIME,ld=$LOAD,mem=$MEM,gw=$GW_STATUS"
