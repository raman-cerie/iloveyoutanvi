#!/usr/bin/env python3
"""φ-Dict v1.0 — Dictionary-aware φ-Codec encoder/decoder.
Usage:
  python3 phi_dict.py encode "φping:n=Oracle"
  python3 phi_dict.py decode "c0a0"
  python3 phi_dict.py compress "φping:n=Oracle"
  python3 phi_dict.py expand "c0a0"
  python3 phi_dict.py dict
"""

import os, sys, re, json

DICT_PATH = os.path.join(os.path.dirname(__file__), "..", "dict", "v1.dict")

# Load dictionary
DICT = {}  # code → word
REV_DICT = {}  # word → code

def _load_dict():
    global DICT, REV_DICT
    DICT = {}
    REV_DICT = {}
    try:
        with open(DICT_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                DICT[k] = v
                REV_DICT[v.lower()] = k
    except FileNotFoundError:
        pass

def _ensure_dict():
    if not DICT:
        _load_dict()

def code_to_word(code):
    """Translate 2-char code to word."""
    _ensure_dict()
    return DICT.get(code, code)

def word_to_code(word):
    """Translate word to 2-char code."""
    _ensure_dict()
    w = word.lower()
    if w in REV_DICT:
        return REV_DICT[w]
    # Also check: single-char field keys might map to reverse values
    # E.g., value "n" → code "p0" through reverse dict
    for code, val in DICT.items():
        if val.lower() == w:
            return code
    return word

def compress(simple_msg):
    """Compress a φ-codec message to φ-dict format.
    φping:n=Oracle → c0a0
    """
    _ensure_dict()
    if not simple_msg.startswith("φ"):
        return simple_msg
    
    # Remove φ prefix
    body = simple_msg[1:]
    
    if ":" in body:
        opcode, payload = body.split(":", 1)
    else:
        opcode, payload = body, ""
    
    # Compress opcode
    op_compressed = word_to_code(opcode)
    
    # Compress key=value fields
    if payload:
        parts = []
        for pair in payload.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                kc = word_to_code(k)
                vc = word_to_code(v)
                if kc == k and vc == v:
                    parts.append(f"{k}={v}")
                else:
                    parts.append(f"{kc}{vc}")
            else:
                parts.append(word_to_code(pair))
        return f"{op_compressed}{','.join(parts)}"
    
    return op_compressed

def expand(compressed):
    """Expand φ-dict compressed message to full φ-codec.
    c0a0 → φping:n=Oracle
    """
    _ensure_dict()
    
    # No comma → single entity
    if "," not in compressed:
        return compressed  # Too short to expand
    
    # First segment before comma is the opcode
    first_seg = compressed.split(",")[0]
    
    # Try to decode as opcode
    opcode = code_to_word(first_seg[:2]) if len(first_seg) >= 2 else first_seg
    remainder = first_seg[2:] if len(first_seg) > 2 else ""
    
    parts = []
    if remainder:
        parts.append(code_to_word(remainder))
    
    for seg in compressed.split(",")[1:]:
        # Each seg is either k=v or k+v where both are 2-char codes
        if "=" in seg:
            k, v = seg.split("=", 1)
            parts.append(f"{code_to_word(k)}={code_to_word(v)}")
        elif len(seg) >= 4:
            k = code_to_word(seg[:2])
            v = code_to_word(seg[2:])
            parts.append(f"{k}={v}")
        elif len(seg) >= 2:
            parts.append(code_to_word(seg))
        else:
            parts.append(seg)
    
    return f"φ{opcode}:{','.join(parts)}"

def decode(raw):
    """Auto-detect and decode any φ-format message."""
    _ensure_dict()
    
    if raw.startswith("φ1:"):
        return _decode_full(raw)
    elif raw.startswith("φ"):
        # φ-codec format — expand then decode
        return {"format": "phi_codec", "message": raw, "expanded": raw}
    
    # φ-dict compressed format — expand
    expanded = expand(raw)
    
    return {"format": "phi_dict", "compressed": raw, "expanded": expanded}

def _decode_full(encoded):
    import base64, zlib, json
    parts = encoded.split(":", 4)
    if len(parts) != 5 or parts[0] != "φ1":
        return None
    _, msg_type, target, opcode, payload = parts
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding
    try:
        decompressed = zlib.decompress(base64.urlsafe_b64decode(payload))
        data = json.loads(decompressed)
    except:
        data = {"_error": "decompress_failed"}
    return {"format": "phi_full", "type": msg_type, "target": target, "opcode": opcode, "data": data}

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  phi_dict.py decode <msg>   — auto-detect + expand")
        print("  phi_dict.py encode <msg>   — encode to φ-codec")
        print("  phi_dict.py compress <msg> — φ-codec → φ-dict")
        print("  phi_dict.py expand <msg>   — φ-dict → φ-codec")
        print("  phi_dict.py dict           — show dictionary")
        return
    
    cmd = sys.argv[1]
    msg = " ".join(sys.argv[2:])
    
    if cmd == "decode":
        result = decode(msg)
        print(json.dumps(result, indent=2))
    elif cmd == "encode":
        print(msg)
    elif cmd == "compress":
        print(compress(msg))
    elif cmd == "expand":
        print(expand(msg))
    elif cmd == "dict":
        _ensure_dict()
        print(f"φ-Dict v1.0: {len(DICT)} entries")
        for code in sorted(DICT.keys()):
            print(f"  {code} → {DICT[code]}")
    else:
        print(f"Unknown: {cmd}")

if __name__ == "__main__":
    main()
