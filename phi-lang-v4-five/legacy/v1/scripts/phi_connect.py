#!/usr/bin/env python3
"""φ-connect: Read Runtime Config → establish SSH mesh.
One-time setup program. Reads node IPs from Notion Runtime Config,
tests SSH to each, reports the mesh state.

The key insight: some nodes can reach out (Jarvis→Oracle ✅),
others need public IPs (Oracle→Jarvis ❌ behind NAT).
This script maps the directional matrix and identifies gaps.
"""

import os, sys, json, urllib.request, subprocess

# ── Config ──────────────────────────────────────────────

NOTION_TOKEN = ""
env_path = os.path.expanduser("~/.hermes/.env")
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#') and line.startswith('NOTION_TOKEN'):
            NOTION_TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

RUNTIME_PAGE = "39e2ea11fbac81828a6fccaa7a485330"
BASE_URL = "https://api.notion.com/v1"

# ── Nodes from Runtime Config ────────────────────────────

NODES = {}
MY_NODE = "Oracle"

def load_nodes():
    """Read node IPs from Runtime Config table."""
    global NODES
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
    }
    
    # Read the page content
    req = urllib.request.Request(
        f"{BASE_URL}/blocks/{RUNTIME_PAGE}/children?page_size=100",
        headers=headers, method="GET"
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    
    # Find the FIRST table (Nodes table) — stop after it
    table_found = False
    for block in resp.get("results", []):
        if block.get("type") == "table" and not table_found:
            table_found = True
            bid = block.get("id")
            row_req = urllib.request.Request(
                f"{BASE_URL}/blocks/{bid}/children?page_size=20",
                headers=headers, method="GET"
            )
            rows = json.loads(urllib.request.urlopen(row_req, timeout=15).read())
            
            for row in rows.get("results", []):
                if row.get("type") == "table_row":
                    cells = row.get("table_row", {}).get("cells", [])
                    if len(cells) >= 4:
                        name = "".join(t.get("plain_text","") for t in cells[0]).strip()
                        ip = "".join(t.get("plain_text","") for t in cells[2]).strip() if len(cells) > 2 else ""
                        user = "".join(t.get("plain_text","") for t in cells[3]).strip() if len(cells) > 3 else "ubuntu"
                        role = "".join(t.get("plain_text","") for t in cells[1]).strip() if len(cells) > 1 else ""
                        
                        # Validate: name should look like a node, IP should look like an IP
                        if name and ip and (ip[0].isdigit() or ip.startswith("N/A")):
                            NODES[name.lower()] = {
                                "name": name,
                                "role": role,
                                "ip": ip,
                                "user": user,
                                "reachable": None,
                                "ssh_test": ""
                            }
            break  # Only process the first table
    
    return NODES

def test_ssh(node_name, node_info):
    """Test SSH connectivity to a node."""
    ip = node_info["ip"]
    user = node_info["user"]
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
             "-o", "BatchMode=yes", "-i", os.path.expanduser("~/.ssh/id_ed25519"),
             f"{user}@{ip}", "echo φpong"],
            capture_output=True, text=True, timeout=10
        )
        if "φpong" in r.stdout:
            node_info["reachable"] = True
            node_info["ssh_test"] = "✅"
        else:
            node_info["reachable"] = False
            node_info["ssh_test"] = f"❌ {r.stderr.strip()[:60]}"
    except subprocess.TimeoutExpired:
        node_info["reachable"] = False
        node_info["ssh_test"] = "❌ timeout"
    except Exception as e:
        node_info["reachable"] = False
        node_info["ssh_test"] = f"❌ {str(e)[:60]}"
    
    return node_info

def is_private_ip(ip):
    """Check if IP is private/LAN."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    first = int(parts[0])
    second = int(parts[1]) if len(parts) > 1 else 0
    return (first == 10 or
            (first == 172 and 16 <= second <= 31) or
            (first == 192 and second == 168))

def main():
    print("φ-connect v1.0 — SSH Mesh Setup\n")
    print("Reading Runtime Config...")
    load_nodes()
    
    if not NODES:
        print("❌ No nodes found in Runtime Config")
        return 1
    
    print(f"Found {len(NODES)} nodes\n")
    
    # Test connectivity
    my_identity = subprocess.run(
        ["cat", os.path.expanduser("~/.ssh/id_ed25519.pub")],
        capture_output=True, text=True
    ).stdout.strip()
    
    print(f"My identity: {MY_NODE}")
    print(f"My key: {my_identity[:60]}...\n")
    
    # Test each node
    for node_name, info in sorted(NODES.items()):
        name = info["name"]
        if name.lower() == MY_NODE.lower():
            print(f"  {name:8} — this is me, skip")
            continue
        
        # Test SSH
        test_ssh(node_name, info)
        
        private = " [⚠️ PRIVATE — need Tailscale/VPN for inbound]" if is_private_ip(info["ip"]) else ""
        print(f"  {name:8} → {info['ip']:>16}@{info['user']} {info['ssh_test']}{private}")
    
    print()
    print("─── Mesh Matrix ───")
    print(f"{'':12} {'Status':10} {'Direction':20}")
    print("-" * 42)
    for n1_name, n1_info in sorted(NODES.items()):
        for n2_name, n2_info in sorted(NODES.items()):
            if n1_name == n2_name:
                continue
            n1_is_me = n1_info["name"].lower() == MY_NODE.lower()
            n2_is_me = n2_info["name"].lower() == MY_NODE.lower()
            
            if n1_is_me:
                # I'm testing outbound
                status = "✅ OPEN" if n2_info.get("reachable") else "❌ CLOSED"
                private = " (NAT)" if is_private_ip(n2_info["ip"]) else ""
                print(f"  {MY_NODE} → {n2_info['name']:8} {status:10} {n2_info['ip']}{private}")
            elif n2_is_me:
                # Others → me (assume yes — sshd is running)
                print(f"  {n1_info['name']:8} → {MY_NODE:8} ✅ OPEN      {n1_info['ip']}")
    
    print()
    print("─── Gaps ───")
    gaps = 0
    for n1_name, n1_info in sorted(NODES.items()):
        for n2_name, n2_info in sorted(NODES.items()):
            if n1_name == n2_name:
                continue
            if n1_info["name"].lower() == MY_NODE.lower() and not n2_info.get("reachable"):
                if is_private_ip(n2_info["ip"]):
                    print(f"  {MY_NODE} → {n2_info['name']}: needs Tailscale/VPN (private IP)")
                else:
                    print(f"  {MY_NODE} → {n2_info['name']}: SSH test failed — check key/port")
                gaps += 1
    
    if gaps == 0:
        print("  ✅ Full mesh — all directions open")
    else:
        print(f"  Total gaps: {gaps}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
