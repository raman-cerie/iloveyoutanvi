#!/usr/bin/env python3
"""φ-lang v3 — Mesh Heartbeat Template
Fires on Cloud Nodes Chat. All messages in φ-code.
GitHub ref: https://github.com/raman-cerie/phi-lang
Rulebook: https://www.notion.so/39f2ea11fbac813f9fb9fd58052410f0
"""

import os, sys, json, time, subprocess, urllib.request
from datetime import datetime

# ═════ CONFIG ═════
NOTION_DB = "39e2ea11-fbac-814b-a02c-c1d93644544a"
RULEBOOK = "39f2ea11-fbac-813f-9fb9-fd58052410f0"
PHI_REPO = "raman-cerie/phi-lang"
PHI_PATH = "~/installations/language/v1"
HOME_PHI = "~/Hermes/home/a/installations/v1/language/phi-lang-v3"
NODE = os.environ.get("PHI_NODE", "a1")  # a0=Oracle a1=Jarvis a2=GCP

# ═════ LOAD TOKEN ═════
token = None
env_path = os.path.expanduser("~/.hermes/.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith("NOTION_TOKEN=") and not line.startswith("#"):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")

# ═════ φ-BLOCK TEMPLATE ═════
def build_heartbeat():
    """Build the φ-lang v3 heartbeat message."""
    now = datetime.utcnow().isoformat() + "Z"
    ts_short = datetime.utcnow().strftime("%H:%M")
    
    # Get system stats
    try:
        load = subprocess.check_output("uptime | awk '{print $(NF-2),$(NF-1),$NF}' | tr -d ','", shell=True).decode().strip()
    except:
        load = "unknown"
    
    try:
        mem = subprocess.check_output("free -h 2>/dev/null | awk '/Mem:/{print $3\"/\"$2}' || vm_stat 2>/dev/null | awk '/Pages active/{a=$NF}/Pages free/{f=$NF}END{printf \"%.0fM\",(a+f)*4096/1048576}'", shell=True).decode().strip()
    except:
        mem = "unknown"

    message = f"""**φ{NODE}:type=h2heartbeat,to=all,ts={now}**

## ⏰ TIME BREAKER — {ts_short} UTC
φdata:topic=mesh_status,ref=RULEBOOK,phi_repo=github.com/{PHI_REPO}

### 📊 Status Check
φstat:n=all,ts={ts_short}
c0na0:n=Oracle,req=b0b1b3j0j1j4  # health, status, load, cpu, disk, ram
c0na1:n=Jarvis,req=b0b1b3j0j1j4
c0na2:n=GCP,req=b0b1b3j0j1j4

**φ{NODE}:local={dict(load=load, mem=mem)}**

### 📋 Work & Plans
φdata:topic=g0g1g3  # work, task, todo
φv8:n=all,req=g0g1g5  # report work, tasks, blocked items

### 🔄 Incremental Tasks
φc4deploy:n=all,service=home,ref=github.com/{PHI_REPO}
φx6s:n=all,task=r1r6k1  # suggest: test commit dict
φif=s0,c4deploy=AUTO_PULL  # if tests pass, auto-deploy

### 🔗 References
- φ-k0k1: https://github.com/{PHI_REPO}
- φ-rulebook: https://www.notion.so/{RULEBOOK.replace('-','')}
- φ-bus: https://www.notion.so/{NOTION_DB.replace('-','')}

### ⚡ Network
- t4s5:n=all,port=9337,proto=UDP  # beacon active
- t4s30:n=all,bus=notion  # polling active
- PROXY: if n1 on any node, neighbor posts on behalf

**φ{NODE}:h2heartbeat,END,s7**"""

    return message

# ═════ POST TO NOTION ═════
def post_bus(message):
    if not token:
        print("[φ] no notion token — printing locally")
        print(message)
        return None
    
    title = f"φrply:h2heartbeat,ts={datetime.utcnow().strftime('%H:%M')},n={NODE},s7"
    url = "https://api.notion.com/v1/pages"
    
    payload = json.dumps({
        "parent": {"database_id": NOTION_DB},
        "properties": {
            "Message": {"title": [{"text": {"content": title[:200]}}]},
            "Node": {"select": {"name": NODE}},
            "Type": {"select": {"name": "Command"}},
            "Status": {"select": {"name": "Done"}}
        },
        "children": [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": message}}]}}
        ]
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2025-09-03",
        "Content-Type": "application/json"
    })

    try:
        resp = json.loads(urllib.request.urlopen(req).read())
        pid = resp["id"].replace("-", "")
        print(f"[φ] heartbeat posted: https://www.notion.so/{pid}")
        return pid
    except Exception as e:
        print(f"[φ] post error: {e}")
        return None

# ═════ MAIN ═════
if __name__ == "__main__":
    hb = build_heartbeat()
    post_bus(hb)
