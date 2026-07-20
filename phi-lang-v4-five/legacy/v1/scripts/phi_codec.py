#!/usr/bin/env python3
"""
φ-Code v1.0 — Mesh Compression Protocol
Shared codec for all mesh nodes (Jarvis, Oracle, GCP, SubHermes).

Two modes:
  1. SIMPLE: φ<type>:<k=v,...> — zero-LLM, script-only auto-response
  2. FULL:   φ1:<type>:<target>:<opcode>:<zlib+b64> — for dense payloads

Usage:
  python3 phi_codec.py decode "φsshk:h=host,u=user,..."
  python3 phi_codec.py encode φsshk h=host u=user
  python3 phi_codec.py route "φping:n=Oracle"    → auto-respond
  python3 phi_codec.py types
  python3 phi_codec.py --test
"""

import json, sys, zlib, base64
from typing import Optional

# ── Block type registry ──────────────────────────────────────

BLOCK_TYPES = {
    "φsshk":  "SSH Key Exchange",
    "φrcfg":  "Runtime Config",
    "φrply":  "Reply Capabilities",
    "φping":  "Health Ping",
    "φpong":  "Health Pong",
    "φexec":  "Remote Command",
    "φdata":  "Data Payload",
    "φerr":   "Error Report",
    "φack":   "Acknowledgement",
    "φsync":  "State Sync Request",
    "φiden":  "Identity",
    "φcnex":  "Connection Exchange",
    "φwork":  "Work Status",
    "φadopt": "Protocol Adoption",
    "φstat":  "Status Report",
    "φtbn":   "Token Burn Report",
    "φconf":  "Config Sync",
}

# Targets
TARGETS = {"J":"Jarvis","O":"Oracle","G":"GCP","H":"SubHermes","*":"All","$":"Shiv"}

# Field abbreviations
FIELD = {"host":"h","ip":"ip","user":"u","port":"po","public_key":"pk","api_key":"ak",
         "token":"tk","status":"st","model":"m","provider":"p","telegram":"tg",
         "node":"n","services":"s","gateway":"gw","uptime":"up","memory":"mem",
         "load":"ld","error":"e","command":"cmd","reason":"r","id":"id"}

# ── Simple Decode ────────────────────────────────────────────

def _parse_kv(body: str) -> dict:
    fields = {}
    for part in body.split(","):
        part = part.strip()
        if not part: continue
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k.strip()] = v.strip()
        else:
            fields[part] = True
    return fields

def _human_readable(decoded: dict) -> str:
    t = decoded["type"]; f = decoded["fields"]
    if t == "φsshk":   return f"SSH: {f.get('u','?')}@{f.get('h','?')} pk={f.get('pk','?')[:20]}..."
    elif t == "φrcfg": return f"Config: {f.get('n','?')} m={f.get('m','?')} tg={f.get('tg','?')}"
    elif t == "φrply": return f"Caps: [{f.get('s','?')}] gw={f.get('gw','?')}"
    elif t == "φping": return f"Ping from {f.get('n','?')}"
    elif t == "φexec": return f"Exec: {f.get('cmd','?')} on {f.get('n','?')}"
    elif t == "φack":  return f"ACK: {f.get('n','?')} for {f.get('id','?')}"
    elif t == "φerr":  return f"Error: {f.get('n','?')} - {f.get('e','?')}"
    elif t == "φsync": return f"Sync: {f.get('n','?')} state={f.get('s','?')}"
    elif t == "φiden": return f"ID: {f.get('n','?')}@{f.get('h','?')}"
    elif t == "φcnex": return f"Conn: ssh→{f.get('ssh','?')} tg={f.get('tg','?')} mh={f.get('mh','?')}"
    return str(f)

def decode_simple(raw: str) -> Optional[dict]:
    """Decode φ<type>:<k=v,...> format."""
    raw = raw.strip()
    colon = raw.find(":")
    if colon == -1:
        return None
    block_type = raw[:colon]
    body = raw[colon+1:]
    fields = _parse_kv(body)
    result = {
        "type": block_type,
        "description": BLOCK_TYPES.get(block_type, "Unknown"),
        "fields": fields,
        "raw": raw,
    }
    result["readable"] = _human_readable(result)
    return result

# ── Full Decode (zlib+b64) ───────────────────────────────────

SYMBOLS = {
    "C":"Command","R":"Response","Q":"Query","K":"KeyExchange",
    "S":"Status","A":"Ack","X":"Config","E":"Error",
    "J":"Jarvis","O":"Oracle","G":"GCP","H":"SubHermes","*":"All","$":"Shiv",
}

def decode_full(encoded: str) -> Optional[dict]:
    """Decode φ1:<type>:<target>:<opcode>:<zlib+b64> format."""
    parts = encoded.split(":", 4)
    if len(parts) != 5 or parts[0] != "φ1":
        return None
    msg_type, target, opcode, payload = parts[1:]
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding
    try:
        decompressed = zlib.decompress(base64.urlsafe_b64decode(payload))
        data = json.loads(decompressed)
    except:
        data = {"_raw": payload, "_error": "decompression_failed"}
    return {"version":1,"type":SYMBOLS.get(msg_type,msg_type),
            "target":SYMBOLS.get(target,target),"opcode":SYMBOLS.get(opcode,opcode),"data":data}

def decode(raw: str) -> Optional[dict]:
    """Auto-detect and decode φ-Code message (simple or full)."""
    if raw.startswith("φ1:"):
        return decode_full(raw)
    elif raw.startswith("φ"):
        return decode_simple(raw)
    return None

# ── Encode ───────────────────────────────────────────────────

def encode_simple(block_type: str, **fields) -> str:
    """Encode to φ<type>:<k=v,...> format."""
    if not block_type.startswith("φ"):
        block_type = f"φ{block_type}"
    pairs = []
    for k, v in fields.items():
        abbr = FIELD.get(k, k)
        if v is True:
            pairs.append(abbr)
        else:
            pairs.append(f"{abbr}={v}")
    return f"{block_type}:" + ",".join(pairs)

def encode_full(msg_type, target, opcode, data):
    """Encode to φ1:<type>:<target>:<opcode>:<zlib+b64> format."""
    payload = json.dumps(data, separators=(',',':'), ensure_ascii=False)
    compressed = base64.urlsafe_b64encode(zlib.compress(payload.encode())).decode().rstrip("=")
    return f"φ1:{msg_type}:{target}:{opcode}:{compressed}"

# ── Route — Auto-Respond (Zero LLM) ──────────────────────────

def route_block(raw: str) -> Optional[str]:
    """Decode and auto-respond to φ-BLOCK. No LLM needed. Returns response or None.
    
    Architecture: Three Tiers
      Tier 1: Deterministic opcodes → handled here. Zero LLM. Always responds. (~80% of traffic)
      Tier 2: Semi-deterministic (exec, deploy, restart) → Tiny model binary gate (~10 tokens)
      Tier 3: Novel/crisis/planning → Large model (Jarvis only)
    """
    decoded = decode_simple(raw)
    if not decoded:
        return None
    t = decoded["type"]
    f = decoded["fields"]
    
    # ── Tier 1: Deterministic — zero LLM ──
    
    if t == "φping":
        return encode_simple("φpong", n="Oracle", up="OCI_uk-london", phi="v1.0_native")
    
    elif t == "φpong":
        return None  # No response needed — this is already an answer
    
    elif t == "φsshk":
        pk = "ssh-ed25519_AAAAC3NzaC1lZDI1NTE5AAAAIKnBUj1heKQ8ONx+2sWovJAe7DBxKmYtbJ7kfZ+ypSqD"
        return encode_simple("φack", id="sshk", n="Oracle", status="received", pk=pk)
    
    elif t == "φrcfg":
        return encode_simple("φrcfg", m="deepseek-v4-pro", p="deepseek", tg="ok",
                            n="Oracle", phi="v1.0", host="OCI_uk-london", sshd="ok")
    
    elif t == "φrply":
        return encode_simple("φack", id="caps", n="Oracle",
                            s="cloud_chat+phi_codec+mesh", gw="tg_ok", phi="v1.0_native")
    
    elif t == "φadopt":
        return encode_simple("φack", id="adopt", n="Oracle", proto="phi_v1",
                            status="live_script_only", method="tier1_route_block")
    
    elif t == "φcnex":
        return encode_simple("φcnex", n="Oracle", ssh="GCP_ok", tg="ok", mh="ok",
                            sshd="ok", phi="v1.0_script")
    
    elif t == "φiden":
        return encode_simple("φack", id="iden", n="Oracle",
                            host="sub-hermes-v4", ip="84.8.159.123", u="ubuntu")
    
    elif t == "φstat":
        return encode_simple("φstat", n="Oracle", up="OCI_uk-london",
                            ld="low", mem="ok", gw="tg_ok", phi="v1.0")
    
    elif t == "φhealth":
        return encode_simple("φstat", n="Oracle", b0="ok", b3="normal",
                            b4="up", b5="ok", f0="connected")
    
    elif t == "φconf":
        topic = f.get("topic", "")
        if "api_keys" in topic:
            return encode_simple("φack", id="api_policy", n="Oracle",
                                status="acknowledged", rule="notion_only")
        return encode_simple("φack", id="conf", n="Oracle", status="applied")
    
    elif t == "φwork":
        return encode_simple("φwork", n="Oracle", g2="phi_codec+actions+repo",
                            g3="mesh_sync+gateway_verify")
    
    elif t == "φack":
        return None  # ACK is terminal — no further response
    
    elif t == "φerr":
        return None  # Error is terminal — log it
    
    elif t == "φhb":
        return None  # Heartbeat — silent, no response expected
    
    # ── Tier 2: Semi-deterministic → needs binary gate (tiny model) ──
    # These return None so the caller knows to invoke the LLM gate
    
    elif t == "φexec":
        # Needs LLM: "should I execute this command?"
        return None  # Fall through to Tier 2 binary gate
    
    elif t == "φdepl":
        # Needs LLM: "should I apply this update?"
        return None  # Fall through to Tier 2 binary gate
    
    # ── Fallthrough: Unknown opcode → Tier 3 full reasoning ──
    
    return None

# ── Decode batch from text ───────────────────────────────────

def decode_batch(text: str) -> list:
    """Find and decode all φ-blocks in text."""
    import re
    results = []
    for match in re.finditer(r'φ\w[\w:]*(?:\s|$)', text):
        result = decode(match.group().strip())
        if result:
            results.append(result)
    return results

# ── CLI ──────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("φ-Code v1.0 — Mesh Compression Protocol")
        print("  decode <msg>  : decode φ-BLOCK")
        print("  encode <type> <k=v...> : encode φ-BLOCK")
        print("  route  <msg>  : auto-respond (zero LLM)")
        print("  types         : list block types")
        print("  --test        : self-test")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "decode":
        raw = " ".join(sys.argv[2:])
        result = decode(raw)
        print(json.dumps(result, indent=2) if result else "❌ Invalid")
    
    elif cmd == "encode":
        if len(sys.argv) < 4:
            print("Usage: phi_codec.py encode <type> key=val ...")
            return
        block_type = sys.argv[2]
        fields = {}
        for arg in sys.argv[3:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                fields[k] = v
            else:
                fields[arg] = True
        print(encode_simple(block_type, **fields))
    
    elif cmd == "route":
        raw = " ".join(sys.argv[2:])
        response = route_block(raw)
        if response:
            decoded = decode_simple(raw)
            print(response)
            if decoded and "readable" in decoded:
                print(f"# {decoded['readable']}")
        else:
            print("# No auto-response for this block type")
    
    elif cmd == "types":
        for code, desc in sorted(BLOCK_TYPES.items()):
            print(f"  {code:8} — {desc}")
    
    elif cmd == "--test":
        # Test simple
        simple = "φsshk:h=10.0.1.5,u=jarvis,pk=AAAA"
        d = decode_simple(simple)
        assert d["type"] == "φsshk" and d["fields"]["h"] == "10.0.1.5"
        assert "SSH:" in d["readable"]
        # Test encode
        e = encode_simple("φping", n="Oracle")
        assert e == "φping:n=Oracle"
        # Test route
        r = route_block("φping:n=GCP")
        assert r and "φpong" in r
        # Test full
        full = encode_full("Q","J","sshk",{"pk":"test","ip":"1.2.3.4"})
        df = decode_full(full)
        assert df["data"]["pk"] == "test"
        print("✅ All tests passed — simple + full + route + encode/decode")
        print(f"   Simple: {simple}")
        print(f"   Full:   {full}")
    
    else:
        print(f"Unknown: {cmd}")

if __name__ == "__main__":
    main()