#!/usr/bin/env python3
"""φ-Actions: opcode → executable handler.
Maps every φ-dict opcode to a script in ~/language/v1/actions/.
Replace: LLM thinking "what should I do?" → direct script execution.

Usage:
  python3 phi_actions.py "c0na0"         # decode + execute
  python3 phi_actions.py exec "c0" "a0"  # direct: opcode target
  python3 phi_actions.py list             # show all opcodes + actions
"""

import os, sys, json, subprocess

ACTIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "actions")

# ── Action Registry: opcode → handler script or inline ──
# Format: opcode → {"handler": "script.sh", "desc": "..."}
# If handler is None, uses inline Python

ACTIONS = {
    "ping": {"handler": "c0_ping.sh",   "desc": "Respond with φpong + system stats"},
    "ack":  {"handler": "c1_ack.sh",    "desc": "Log acknowledgement"},
    "exec": {"handler": "c2_exec.sh",   "desc": "Execute system command"},
    "reply":{"handler": "c3_reply.sh",  "desc": "Post φ-codec response to bus"},
    "deploy":{"handler":"c4_deploy.sh", "desc": "Deploy update from repo"},
    "adopt":{"handler":"c5_adopt.sh",   "desc": "Acknowledge protocol adoption"},
    
    "stat": {"handler": "b0_stat.sh",   "desc": "Report node stats (uptime, load, mem, gw)"},
    "health":{"handler":"b0_stat.sh",   "desc": "Alias for stat"},
    
    "config":{"handler":"d0_config.sh", "desc": "Update local config"},
    
    "sshk":  {"handler": "e0_sshk.sh",  "desc": "Exchange SSH keys"},
    "rcfg":  {"handler": "e1_rcfg.sh",  "desc": "Request runtime config"},
    "apik":  {"handler": "e2_apik.sh",  "desc": "Request API key"},
    
    "cnex":  {"handler": None, "desc": "Report connection status"},
    "work":  {"handler": None, "desc": "Report current work/todo"},
    "ping":  {"handler": "c0_ping.sh",  "desc": "Respond with φpong"},
}

def load_phi_dict():
    """Load φ-dict for opcode→name mapping."""
    dict_path = os.path.join(os.path.dirname(__file__), "..", "dict", "v1.dict")
    d = {}
    if os.path.exists(dict_path):
        with open(dict_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    d[k.strip()] = v.strip()
    return d

def opcode_to_name(opcode_code):
    """Convert 2-char opcode code to name."""
    d = load_phi_dict()
    return d.get(opcode_code, opcode_code)

def resolve_action(opcode):
    """Find the action script for an opcode."""
    # opcode can be 2-char code (c0) or name (ping)
    d = load_phi_dict()
    rev = {v.lower(): k for k, v in d.items()}
    
    if len(opcode) == 2:
        name = d.get(opcode, opcode)
    else:
        name = opcode.lower()
        code = rev.get(name, name)
    
    info = ACTIONS.get(name)
    if not info:
        return None, None, None
    
    return name, info.get("handler"), info.get("desc")

def execute(opcode, target=None, params=None):
    """Execute an opcode's action."""
    name, handler, desc = resolve_action(opcode)
    if not handler:
        # Inline execution for simple handlers
        return f"φack:opcode={name},status=executed_inline"
    
    handler_path = os.path.join(ACTIONS_DIR, handler)
    if not os.path.exists(handler_path):
        return f"φerr:handler={handler},reason=not_found"
    
    # Build args
    args = [handler_path]
    if target:
        args.append(target)
    if params:
        args.extend(params)
    
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        output = result.stdout.strip() or result.stderr.strip()
        return output or f"φack:opcode={name},handler={handler},exit={result.returncode}"
    except subprocess.TimeoutExpired:
        return f"φerr:opcode={name},handler={handler},reason=timeout"
    except Exception as e:
        return f"φerr:opcode={name},handler={handler},reason={str(e)[:50]}"

def decode_and_execute(raw_msg):
    """Decode φ-dict message, resolve opcode, execute action."""
    d = load_phi_dict()
    rev = {v.lower(): k for k, v in d.items()}
    
    # Parse: c0na0 → opcode=c0, target=a0, rest=na0
    if raw_msg.startswith("φ"):
        raw_msg = raw_msg[1:]
    
    # First 2 chars = opcode code
    opcode_code = raw_msg[:2]
    rest = raw_msg[2:]
    
    # Find target (next 2 chars if they match a target code)
    target_code = None
    params = []
    if len(rest) >= 2:
        potential_target = rest[:2]
        target_name = d.get(potential_target, "")
        if target_name and target_name in ("Oracle","Jarvis","GCP","Shiv","SubHermes"):
            target_code = potential_target
            rest = rest[2:]
    
    # Rest is key=value pairs
    if rest:
        for pair in rest.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                params.append(f"{k}={v}")
            else:
                params.append(pair)
    
    opcode_name = d.get(opcode_code, opcode_code)
    target_name = d.get(target_code, target_code) if target_code else None
    
    return execute(opcode_name, target_name, params)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  phi_actions.py <φ-dict msg>  — decode + execute")
        print("  phi_actions.py exec <opcode> [target] [params...]")
        print("  phi_actions.py list           — show action registry")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        d = load_phi_dict()
        print(f"{'Opcode':8} {'Name':12} {'Action':20} {'Description'}")
        print("-" * 60)
        for code, name in sorted(d.items()):
            if any(code[0] == c for c in "abcdefg"):
                action_info = ACTIONS.get(name.lower())
                handler = (action_info.get("handler", "─") if action_info else "─")[:18]
                desc = (action_info.get("desc", "") if action_info else "")[:30]
                print(f"{code:8} {name:12} {handler:20} {desc}")
    
    elif cmd == "exec" and len(sys.argv) >= 3:
        opcode = sys.argv[2]
        target = sys.argv[3] if len(sys.argv) > 3 else None
        params = sys.argv[4:] if len(sys.argv) > 4 else []
        print(execute(opcode, target, params))
    
    else:
        result = decode_and_execute(" ".join(sys.argv[1:]))
        if result:
            print(result)
        else:
            print(f"φerr:reason=no_action,msg={' '.join(sys.argv[1:])}")

if __name__ == "__main__":
    main()
