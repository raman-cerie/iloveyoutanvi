## cloud_chat.py - phi-lang native mesh communication daemon
## Two-layer bus: Notion (primary) + Tailscale UDP (fallback)
## Grammar: poll interval, phi-codec, proxy rules
## Usage: python3 cloud_chat.py [--beacon-only|--poll-only|--full]

import os, sys, json, time, socket, struct, urllib.request, hashlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.expanduser("~/Hermes v3/v4/home/a/installations/v1/phi-lang/v4"))
import phi_codec_v4

# v4 codec singleton
_codec = phi_codec_v4.Codec()

## Configuration
CONFIG = {
    "node_id": os.environ.get("PHI_NODE", "a1"),
    "poll_interval": 30,
    "beacon_interval": 5,
    "heartbeat_interval": 3600,     # 1 hour — mesh status sync
    "beacon_port": 9337,
    "beacon_group": "100.109.149.93",
    "notion_db_id": os.environ.get("NOTION_CLOUD_CHAT_DB", "39e2ea11-fbac-814b-a02c-c1d93644544a"),
    "notion_token": None,
    "proxy_enabled": True,
    "max_beacon_age": 120,
    "rulebook": "39f2ea11-fbac-813f-9fb9-fd58052410f0",
    "phi_repo": "raman-cerie/phi-lang",
}

## Load Notion token from env
def load_token():
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("NOTION_TOKEN=") and not line.startswith("#"):
                    CONFIG["notion_token"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return True
    return False

## Notion Bus — Poll & Post
def poll_notion_bus():
    """Poll Cloud Nodes Chat for new entries since last check."""
    if not CONFIG["notion_token"]:
        return []
    
    url = f"https://api.notion.com/v1/databases/{CONFIG['notion_db_id']}/query"
    payload = json.dumps({
        "page_size": 5,
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]
    }).encode()
    
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {CONFIG['notion_token']}",
        "Notion-Version": "2025-09-03",
        "Content-Type": "application/json"
    })
    
    try:
        resp = json.loads(urllib.request.urlopen(req).read())
        return resp.get("results", [])
    except Exception as e:
        print(f"[notion] poll error: {e}")
        return []

def post_to_bus(message_phi, message_title):
    """Post a phi-BLOCK entry to Cloud Nodes Chat."""
    if not CONFIG["notion_token"]:
        print("[notion] no token — cannot post")
        return False
    
    url = "https://api.notion.com/v1/pages"
    payload = json.dumps({
        "parent": {"database_id": CONFIG["notion_db_id"]},
        "properties": {
            "Message": {"title": [{"text": {"content": message_title[:200]}}]},
            "Node": {"select": {"name": CONFIG["node_id"]}},
            "Type": {"select": {"name": "Response"}},
            "Status": {"select": {"name": "Done"}}
        },
        "children": [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": message_phi}}]}}
        ]
    }).encode()
    
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {CONFIG['notion_token']}",
        "Notion-Version": "2025-09-03",
        "Content-Type": "application/json"
    })
    
    try:
        resp = json.loads(urllib.request.urlopen(req).read())
        print(f"[notion] posted: {resp['id'][:8]}...")
        return True
    except Exception as e:
        print(f"[notion] post error: {e}")
        return False

def proxy_post(sender_node, message_phi, message_title):
    """Write to bus on behalf of a node that can't reach Notion."""
    proxy_msg = f"**φ-proxy:from={sender_node},via={CONFIG['node_id']},ts={datetime.utcnow().isoformat()}Z**"
    full = f"{proxy_msg}\n\n{message_phi}"
    post_to_bus(full, f"φrply:proxy={sender_node},via={CONFIG['node_id']}")
    print(f"[proxy] posted on behalf of {sender_node}")

## Tailscale UDP Beacon Layer
def send_beacon():
    """Broadcast a UDP beacon to the mesh with node status."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # Build beacon: c0na1 (ping + node_id)
    beacon = f"c0n{CONFIG['node_id']}"
    
    try:
        sock.sendto(beacon.encode(), (CONFIG["beacon_group"], CONFIG["beacon_port"]))
        print(f"[beacon] sent: {beacon}")
    except Exception as e:
        print(f"[beacon] send error: {e}")
    finally:
        sock.close()

def listen_beacons():
    """Listen for phi UDP beacons from other nodes on the mesh."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(CONFIG["poll_interval"])
    
    try:
        sock.bind(("0.0.0.0", CONFIG["beacon_port"]))
        data, addr = sock.recvfrom(1024)
        beacon = data.decode()
        src_ip = addr[0]
        
        print(f"[beacon] received: {beacon} from {src_ip}")
        
        # Decode beacon with v4 codec
        decoded = _codec.decode(beacon) if beacon else beacon
        
        # If beacon says node is dark (can't reach Notion), proxy for them
        if CONFIG["proxy_enabled"] and "n0" not in decoded:  # n0=online -> node is dark
            sender = _map_ip_to_node(src_ip)
            proxy_msg = f"φrply:s=beacon_proxy,from={sender},via={CONFIG['node_id']}\ndata:{decoded}"
            proxy_post(sender, proxy_msg, f"φbeacon:from={sender},proxied_by={CONFIG['node_id']}")
        
        return decoded, src_ip
    except socket.timeout:
        return None, None
    except Exception as e:
        print(f"[beacon] listen error: {e}")
        return None, None
    finally:
        sock.close()

def _map_ip_to_node(ip):
    """Map Tailscale IP to node code."""
    mapping = {
        "100.109.149.93": "a0",  # Oracle
        "100.77.235.34": "a1",   # Jarvis
        "100.118.149.98": "a2",  # GCP
    }
    return mapping.get(ip, "a3")  # a3=unknown

## Heartbeat — hourly mesh status sync (Tier 1, zero LLM)
def send_heartbeat():
    """Post the hourly φ-status heartbeat to the bus. Deterministic, zero LLM."""
    now = datetime.utcnow()
    ts = now.isoformat() + "Z"
    ts_short = now.strftime("%H:%M")

    # Collect live stats
    import subprocess
    try:
        uptime = subprocess.check_output("uptime -p 2>/dev/null | cut -d' ' -f2- || uptime | awk -F'up ' '{print $2}' | cut -d',' -f1", shell=True).decode().strip()
    except:
        uptime = "unknown"
    try:
        load = subprocess.check_output("uptime | awk -F'load averages:' '{print $2}' | tr -d ' ' || uptime | awk '{print $(NF-2),$(NF-1),$NF}' | tr -d ','", shell=True).decode().strip()
    except:
        load = "unknown"
    try:
        mem = subprocess.check_output("vm_stat 2>/dev/null | awk '/Pages active/{a=$NF}/Pages free/{f=$NF}/Pages wired/{w=$NF}END{printf \"%.0fM\",(a+w)*4096/1048576}' || free -h 2>/dev/null | awk '/Mem:/{print $3}'", shell=True).decode().strip()
    except:
        mem = "unknown"
    try:
        disk = subprocess.check_output("df -h / 2>/dev/null | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'", shell=True).decode().strip()
    except:
        disk = "unknown"

    # Build φ-format heartbeat
    hb = f"""**φ-{CONFIG['node_id']}:type=h2heartbeat,to=all,ts={ts}**

## ⏰ TIME BREAKER — {ts_short} UTC
φdata:topic=mesh_status,ref=RULEBOOK,phi_repo=github.com/{CONFIG['phi_repo']}

### 📊 Live Stats — {CONFIG['node_id']}
b4=uptime,value={uptime}
b3=load,value={load}
j4=ram_used,value={mem}
j1=disk,value={disk}

### 📊 Status Check — All Nodes
c0na0:n=Oracle,req=b0b1b3j0j1j4  # health status load cpu disk ram
c0na2:n=GCP,req=b0b1b3j0j1j4
φv8:n=all,req=g0g1g5  # report work tasks blocked

### 🔗 Refs
- φ-k0k1: github.com/{CONFIG['phi_repo']}
- φ-rulebook: notion.so/{CONFIG['rulebook'].replace('-','')}

### ⚡ Network
t4s5:n=all,port={CONFIG['beacon_port']},proto=UDP
t4s30:n=all,bus=notion
PROXY:s7,if_n1_proxy_active

**φ-{CONFIG['node_id']}:h2heartbeat,END,s7**"""

    title = f"φ:n={CONFIG['node_id']},ts={ts_short},up={uptime},ld={load},mem={mem}"
    result = post_to_bus(hb, title)
    
    # Classify + Telegram alert (Tier 1 gate via classifier.py)
    try:
        import classifier
        stats = {
            "load": float(load.split()[0]) if load != "unknown" else 0,
            "mem_pct": float(mem.replace('M','').replace('%','')) if mem.replace('M','').replace('%','').isdigit() else 0,
            "disk_pct": float(disk.split('(')[1].replace('%','').replace(')','')) if '(' in disk else 0
        }
        overall, alerts, tg_needed = classifier.Classifier.assess(stats)
        
        # Add classification to heartbeat title
        title = f"φ:n={CONFIG['node_id']},ts={ts_short},up={uptime},ld={load},mem={mem},{overall}"
        
        if tg_needed:
            criticals = [f"{k}={v}" for k,v in alerts.items() if v == "s6"]
            tg_msg = f"{overall},n={CONFIG['node_id']}," + ",".join(criticals)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            action_path = os.path.join(script_dir, "..", "actions", "v5_notify_tg.sh")
            subprocess.run(["bash", action_path, tg_msg], capture_output=True, timeout=5)
    except Exception:
        pass  # silent fallback — classifier optional
    
    return result

## Route incoming messages
def route_message(message_text):
    """Route decoded message to appropriate handler (Tier 1-3). Uses v4 codec."""
    
    # Tier 1: Deterministic — encode and route to shell action
    if "ping" in message_text.lower() or "pong" in message_text.lower():
        action = "c0_ping.sh"
        return "tier1", action
    
    if "ack" in message_text.lower():
        action = "c1_ack.sh" 
        return "tier1", action
    
    if "exec" in message_text.lower():
        # Tier 2: Binary gate — needs token check
        action = "c2_exec.sh"
        return "tier2", action
    
    # Tier 1: φ-lang v4 execution — detect 3-char codes
    phi_codes = __import__('re').findall(r'\b[a-z0-9]{3}\b', message_text)
    if phi_codes and len(phi_codes) >= 1:
        return "phi_exec", message_text
    
    if "deploy" in message_text.lower() or "push" in message_text.lower():
        action = "c4_deploy.sh"
        return "tier2", action
    
    if "restart" in message_text.lower() or "r9" in message_text.lower():
        action = "r9_restart.sh"
        return "tier1", action
    
    if "notify" in message_text.lower() or "tg" in message_text.lower() or "v5" in message_text.lower():
        action = "v5_notify_tg.sh"
        return "tier1", action
    
    # Tier 3: Full reasoning needed
    return "tier3", None

## Main loop
def main():
    print(f"[cloud_chat] starting node={CONFIG['node_id']}")
    print(f"[cloud_chat] poll_interval={CONFIG['poll_interval']}s beacon_interval={CONFIG['beacon_interval']}s")
    
    load_token()
    last_beacon = 0
    last_heartbeat = 0
    last_notion_post = datetime.utcnow().timestamp()
    
    while True:
        now = time.time()
        
        # 1. Listen for Tailscale beacons (non-blocking, with timeout)
        decoded, src = listen_beacons()
        if decoded:
            tier, action = route_message(decoded)
            print(f"[route] from={src} tier={tier} action={action}")
        
        # 2. Poll Notion bus
        entries = poll_notion_bus()
        for entry in entries:
            title_prop = None
            for k, v in entry.get("properties", {}).items():
                if v.get("type") == "title":
                    title_arr = v.get("title", [])
                    title_prop = "".join(t.get("plain_text", "") for t in title_arr)
            
            if title_prop:
                tier, action = route_message(title_prop)
                if tier == "phi_exec":
                    # Execute φ-lang v4 code directly (zero LLM)
                    try:
                        sys.path.insert(0, os.path.expanduser("~/Hermes v3/v4/home/a/installations/v1/phi-lang/v4"))
                        from phi_runtime import Runtime
                        r = Runtime()
                        result = r.execute(action, verbose=False)
                        status = result.get('overall', 's6')
                        print(f"[phi_exec] {action[:50]}... → {status}")
                        post_to_bus(f"φr:{status},{action[:100]}", f"φrply:{status},execed")
                    except Exception as e:
                        print(f"[phi_exec] error: {e}")
                else:
                    print(f"[notion] {entry['id'][:8]}... tier={tier}")
        
        # 3. Send beacon (every beacon_interval seconds)
        if now - last_beacon >= CONFIG["beacon_interval"]:
            send_beacon()
            last_beacon = now
        
        # 4. Send heartbeat (every heartbeat_interval seconds — Tier 1, zero LLM)
        if now - last_heartbeat >= CONFIG["heartbeat_interval"]:
            send_heartbeat()
            last_heartbeat = now
        
        time.sleep(CONFIG["poll_interval"])

if __name__ == "__main__":
    main()
