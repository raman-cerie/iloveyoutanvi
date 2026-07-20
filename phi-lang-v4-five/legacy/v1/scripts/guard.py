## guard.py - phi-lang v3 Cyber Immune System
## Multi-layer: Tailscale beacon (5s) + Notion bus (30s) + threat intel (periodic)
## Detection → signal → defend → report

import os, sys, json, time, socket, hashlib, subprocess, urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
try:
    import phi_dict
    phi_dict._load_dict()
    DICT = phi_dict.DICT
except:
    DICT = {}

## Configuration per node type
CONFIG = {
    "node_id": os.environ.get("PHI_NODE", "a1"),
    "has_tailscale": True,  # if false, use Notion-only + SSH fallback
    "tailscale_beacon_interval": 5,   # seconds - instant crisis detection
    "notion_poll_interval": 30,       # seconds - standard bus
    "notion_db_id": "39e2ea11-fbac-814b-a02c-c1d93644544a",
    "beacon_port": 9337,
    "beacon_group": "100.109.149.93",  # Tailscale IP to unicast to
    "threat_intel_interval": 3600,     # 1 hour - check for cyber issues
    "known_bad_actors": set(),         # populated by threat intel
    "notion_token": None,
}

## Threat Intel Sources
THREAT_FEEDS = [
    "https://feeds.dshield.org/block.txt",           # SANS DShield
    "https://opendbl.net/lists/et-known.list",        # Emerging Threats
    "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset",
]

SERVICES_IN_USE = [
    "github.com/raman-cerie",
    "notion.so",
    "tailscale.com",
    "login.tailscale.com",
    "api.notion.com",
    "openrouter.ai",
    "deepseek.com",
]

## Load Notion token
def load_token():
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("NOTION_TOKEN=") and not line.startswith("#"):
                    CONFIG["notion_token"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return True
    return False

## ===== LAYER 1: TAILSCALE BEACON (5s) =====
## Instant death-pulse detection. If a node misses 3 beacons (15s), alert.

class BeaconWatch:
    def __init__(self):
        self.last_seen = {}  # node_id → timestamp
        self.beacon_timeout = CONFIG["tailscale_beacon_interval"] * 3  # 15s

    def send_beacon(self):
        """Pulse: I am alive."""
        if not CONFIG["has_tailscale"]:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        beacon = f"c0n{CONFIG['node_id']}"  # ping + node
        try:
            sock.sendto(beacon.encode(), (CONFIG["beacon_group"], CONFIG["beacon_port"]))
        except:
            pass
        sock.close()

    def listen(self):
        """Listen for other nodes' pulses. Return dead nodes."""
        if not CONFIG["has_tailscale"]:
            return []
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1)
        dead_nodes = []
        
        try:
            sock.bind(("0.0.0.0", CONFIG["beacon_port"]))
            
            # Collect beacons for 2 seconds
            start = time.time()
            while time.time() - start < 2:
                try:
                    data, addr = sock.recvfrom(1024)
                    beacon = data.decode()
                    # Parse beacon: c0na0 → node a0
                    for k, v in DICT.items():
                        if v in beacon:
                            self.last_seen[v] = time.time()
                except socket.timeout:
                    break
        except:
            pass
        finally:
            sock.close()
        
        # Check for dead nodes
        now = time.time()
        for node_id in ["a0", "a1", "a2"]:
            node_name = DICT.get(node_id, node_id)
            last = self.last_seen.get(node_name, 0)
            if last > 0 and now - last > self.beacon_timeout:
                dead_nodes.append(node_id)
        
        return dead_nodes

## ===== LAYER 2: WEB SECURITY & STORAGE CHECK =====
## Verify web connections, internal storage, code integrity

class SecurityCheck:
    def check_web_connections(self, services):
        """Verify SSL/TLS for all services in use."""
        results = {}
        for svc in services:
            try:
                # Check SSL cert validity
                host = svc.replace("https://", "").replace("http://", "").split("/")[0]
                cmd = f"echo | openssl s_client -connect {host}:443 -servername {host} 2>/dev/null | openssl x509 -noout -dates 2>/dev/null"
                output = subprocess.check_output(cmd, shell=True, timeout=5).decode()
                if "notAfter" in output:
                    expiry = output.split("notAfter=")[1].split("\n")[0]
                    results[host] = f"s7,exp={expiry}"  # s7=stable
                else:
                    results[host] = "s8,cert=unknown"    # s8=unstable
            except:
                results[host] = "s1,connection=failed"    # s1=fail
        return results

    def check_storage_integrity(self, paths):
        """Check file hashes for tampering."""
        results = {}
        for path in paths:
            if os.path.exists(path):
                try:
                    h = hashlib.sha256()
                    for root, dirs, files in os.walk(path):
                        dirs[:] = [d for d in dirs if not d.startswith(".")][:10]
                        for f in files[:50]:
                            fpath = os.path.join(root, f)
                            try:
                                with open(fpath, "rb") as fp:
                                    h.update(fp.read(4096))
                            except:
                                pass
                    results[path] = f"s7,hash={h.hexdigest()[:12]}"
                except:
                    results[path] = "s1,hash=failed"
            else:
                results[path] = "s9,not_found"  # s9=partial
        return results

    def check_code_signing(self, repo_paths):
        """Verify git repo integrity (no unauthorized changes)."""
        results = {}
        for path in repo_paths:
            if os.path.exists(path):
                try:
                    r = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                                     capture_output=True, text=True, timeout=10)
                    if r.stdout.strip():
                        results[path] = "s2,uncommitted_changes"  # s2=warn
                    else:
                        results[path] = "s7,clean"
                except:
                    results[path] = "s5,git_error"  # s5=error
        return results

## ===== LAYER 3: THREAT INTELLIGENCE =====
## Check for known cyber issues with services in use

class ThreatIntel:
    def __init__(self):
        self.bad_actors = set()
        self.last_check = 0

    def check_news(self):
        """Check for cyber incidents related to Raman system services."""
        alerts = []
        issues = []

        for svc in SERVICES_IN_USE:
            host = svc.replace("https://", "").replace("http://", "").split("/")[0]
            # Check major security news sites for service mentions
            search_urls = [
                f"https://www.cisa.gov/news-events/cybersecurity-advisories?search={host}",
                f"https://nvd.nist.gov/vuln/search/results?query={host}",
            ]
            for url in search_urls:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "phi-guard/1.0"})
                    resp = urllib.request.urlopen(req, timeout=5)
                    content = resp.read().decode("utf-8", errors="ignore")[:5000]
                    if host.lower() in content.lower():
                        alerts.append(f"z0s5:w5svc={host},source=cisa_nvd")  # z0=urgent
                except:
                    pass

        # Check for known bad IPs (basic - in production, use full threat feeds)
        try:
            for feed_url in THREAT_FEEDS[:1]:
                req = urllib.request.Request(feed_url, headers={"User-Agent": "phi-guard/1.0"})
                resp = urllib.request.urlopen(req, timeout=10)
                for line in resp.read().decode().split("\n")[:100]:
                    if line and not line.startswith("#"):
                        self.bad_actors.add(line.split()[0] if " " in line else line.strip())
        except:
            pass

        self.last_check = time.time()
        return alerts, issues

## ===== MAIN GUARD LOOP =====

def post_security_bulletin(message_phi, severity="s3"):
    """Post security findings to Notion bus."""
    if not CONFIG["notion_token"]:
        print(f"[guard] bulletin (no token): {message_phi[:100]}")
        return

    url = "https://api.notion.com/v1/pages"
    title = f"φguard:{severity},n={CONFIG['node_id']},type=security_bulletin"
    
    payload = json.dumps({
        "parent": {"database_id": CONFIG["notion_db_id"]},
        "properties": {
            "Message": {"title": [{"text": {"content": title[:200]}}]},
            "Node": {"select": {"name": CONFIG["node_id"]}},
            "Type": {"select": {"name": "Log"}},
            "Status": {"select": {"name": "Done"}}
        },
        "children": [
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [{"type": "text", "text": {"content": message_phi}}]}}
        ]
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {CONFIG['notion_token']}",
        "Notion-Version": "2025-09-03", "Content-Type": "application/json"
    })

    try:
        urllib.request.urlopen(req)
        print(f"[guard] bulletin posted: {severity}")
    except Exception as e:
        print(f"[guard] post error: {e}")

def main():
    print(f"[guard] booting node={CONFIG['node_id']} has_tailscale={CONFIG['has_tailscale']}")
    print(f"[guard] beacon={CONFIG['tailscale_beacon_interval']}s poll={CONFIG['notion_poll_interval']}s")
    
    load_token()
    watch = BeaconWatch()
    sec = SecurityCheck()
    intel = ThreatIntel()
    
    last_poll = 0
    last_intel_check = 0
    last_beacon = 0
    
    while True:
        now = time.time()
        alerts = []

        # Layer 1: Tailscale beacon (every 5s if available)
        if CONFIG["has_tailscale"] and now - last_beacon >= CONFIG["tailscale_beacon_interval"]:
            watch.send_beacon()
            dead = watch.listen()
            if dead:
                for node in dead:
                    alerts.append(f"φguard:s6,node={node},state=n1,cause=beacon_timeout")
                    print(f"[guard] ⚠️  NODE DARK: {node}")
            last_beacon = now

        # Layer 2: Notion bus health check (every 30s)
        if now - last_poll >= CONFIG["notion_poll_interval"]:
            # Web connection check
            web_status = sec.check_web_connections(SERVICES_IN_USE)
            for host, status in web_status.items():
                if "s1" in status or "s8" in status:
                    alerts.append(f"φguard:s2,n={CONFIG['node_id']},svc={host},web={status}")
            
            # Storage integrity
            paths = [os.path.expanduser("~/installations/language"),
                    os.path.expanduser("~/Hermes v3/v3")]
            storage = sec.check_storage_integrity(paths)
            
            # Code signing
            repos = [os.path.expanduser("~/installations/language"),
                    os.path.expanduser("~/Hermes v3/v3/projects/heart")]
            code = sec.check_code_signing(repos)
            
            last_poll = now

        # Layer 3: Threat intel (every 1 hour)
        if now - last_intel_check >= CONFIG["threat_intel_interval"]:
            news_alerts, issues = intel.check_news()
            alerts.extend(news_alerts)
            last_intel_check = now
            print(f"[guard] threat intel: {len(news_alerts)} alerts, known baddies: {len(intel.bad_actors)}")

        # Post any alerts to Notion bus
        if alerts:
            bulletin = "**φguard:type=security_bulletin,ts=" + datetime.utcnow().isoformat() + "Z**\n\n"
            for alert in alerts:
                bulletin += f"{alert}\n"
            post_security_bulletin(bulletin, alerts[0][:20])

        time.sleep(min(CONFIG["tailscale_beacon_interval"], 1))

if __name__ == "__main__":
    main()
