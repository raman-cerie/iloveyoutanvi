#!/bin/bash
# φ-lang v3 — r9_restart.sh
# Restart cloud_chat daemon on target node
# Usage: bash r9_restart.sh <node_id>  (a0=Oracle a1=Jarvis a2=GCP)
# φ-code: r9 (restart)

NODE="${1:-a1}"
NODE_NAME=""
TAILSCALE_IP=""
PHI_HOME="$HOME/installations/language/v1"

case "$NODE" in
    a0) NODE_NAME="Oracle"; TAILSCALE_IP="100.109.149.93"; SSH_USER="ubuntu";;
    a1) NODE_NAME="Jarvis"; TAILSCALE_IP="100.77.235.34"; SSH_USER="shivansh";;
    a2) NODE_NAME="GCP"; TAILSCALE_IP="100.118.149.98"; SSH_USER="shivansh";;
    *)  echo "φerror:n=$NODE,reason=unknown_node"; exit 1;;
esac

echo "φr9:restarting=$NODE_NAME,ip=$TAILSCALE_IP"

# Self-restart
if [ "$NODE" = "$PHI_NODE" ] || [ "$NODE" = "$(hostname)" ]; then
    echo "φr9:self,action=restart"
    pkill -f "cloud_chat.py" 2>/dev/null
    sleep 1
    cd "$PHI_HOME" && nohup python3 -u scripts/cloud_chat.py > /tmp/cloud_chat.log 2>&1 &
    echo "φr9:self,done,PID=$!"
    exit 0
fi

# Remote restart via Tailscale SSH
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$SSH_USER@$TAILSCALE_IP" \
    "cd $PHI_HOME && pkill -f cloud_chat.py 2>/dev/null; sleep 1; nohup python3 -u scripts/cloud_chat.py > /tmp/cloud_chat.log 2>&1 & echo 'PID='\$!" 2>&1

echo "φr9:$NODE_NAME,done,s7"
