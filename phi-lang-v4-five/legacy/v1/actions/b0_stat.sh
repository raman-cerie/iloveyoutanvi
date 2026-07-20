#!/bin/bash
# b0_stat.sh — Full node status report (cross-platform)
# macOS + Linux compatible. Zero LLM.

NODE_NAME="${1:-Oracle}"

# Cross-platform uptime
if [[ $(uname) == "Darwin" ]]; then
    UPTIME_RAW=$(uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}')
else
    UPTIME_RAW=$(uptime -p 2>/dev/null | sed 's/up //' || uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}')
fi

# Load average
LOAD=$(uptime | awk -F'load average:|load averages:' '{print $2}' | xargs | awk '{print $1,$2,$3}')

# Memory
if [[ $(uname) == "Darwin" ]]; then
    PAGE_SIZE=$(vm_stat | awk '/page size/ {print $NF}')
    FREE_PAGES=$(vm_stat | awk '/Pages free/ {gsub(/\./,""); print $NF}')
    ACTIVE_PAGES=$(vm_stat | awk '/Pages active/ {gsub(/\./,""); print $NF}')
    MEM_USED=$(( ($ACTIVE_PAGES * $PAGE_SIZE) / 1048576 ))
    MEM_TOTAL=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1048576)}')
    MEM="${MEM_USED}/${MEM_TOTAL}Mi"
else
    MEM_USED=$(free -m 2>/dev/null | awk '/Mem:/ {print $3}')
    MEM_TOTAL=$(free -m 2>/dev/null | awk '/Mem:/ {print $2}')
    MEM="${MEM_USED}/${MEM_TOTAL}Mi"
fi

# Disk
DISK=$(df -h / 2>/dev/null | awk 'NR==2 {print $4" free / "$2" total"}')

# Gateway check
GW_STATUS="unknown"
curl -s --connect-timeout 2 http://localhost:8080/health >/dev/null 2>&1 && GW_STATUS="ok" || GW_STATUS="no_gateway"

# Python
PY_VERSION=$(python3 --version 2>/dev/null || echo "missing")

echo "φstat:n=$NODE_NAME,up=$UPTIME_RAW,ld=$LOAD,mem=$MEM,disk=$DISK,gw=$GW_STATUS,py=$PY_VERSION,phi=v1.0"
