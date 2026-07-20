# φ-codec v5 — Session-Persistent 2-Char Compression Protocol

> Spec v1.0 · 2026-07-18
> Ascending base36 word encoding with session-persistent a.dict

---

## Core Concept

Every word longer than 2 characters gets a **2-character base36 code** (0-9, a-z = 36 chars, 36² = 1,296 positions). Short words (≤2 chars) stay as English. The code IS the position in an ordered array called `a.dict`.

```
a.dict = ["the", "mesh", "network", "has", ...]
          ↑pos0   ↑pos1    ↑pos2      ↑pos3

"the"     → code "00"  (a.dict[0])
"mesh"    → code "01"  (a.dict[1])
"network" → code "02"  (a.dict[2])
```

No mapping table. No schema overhead. `a.dict` is both the dictionary AND the schema.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      SESSION LIFECYCLE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  MESSAGE 1 (SETUP):                                          │
│  ────────────────                                            │
│  User sends: [encoder.py] + [a.dict₀] + [2char_prompt₁]    │
│  LLM receives → decodes → thinks → replies                  │
│  LLM outputs: [2char_reply₁] + [delta_dict₁]                │
│  User appends delta → a.dict₁ = a.dict₀ + delta_dict₁       │
│                                                              │
│  MESSAGE 2+ (STEADY STATE):                                  │
│  ─────────────────────────                                   │
│  User sends: [2char_promptₙ]  ← NO a.dict, NO script       │
│  LLM has a.dict in Python memory, decodes instantly          │
│  LLM outputs: [2char_replyₙ] + [delta_dictₙ]               │
│  User appends delta                                         │
│                                                              │
│  a.dict grows session-long, plateaus at ~500-800 words,      │
│  then each message is pure 2char → 50% smaller than English  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Structures

### `a.dict` — The Ordered Word Array

```python
a_dict = []  # index = position = code in base36
```

| Index | Base36 Code | Word |
|---|---|---|
| 0 | "00" | "the" |
| 1 | "01" | "mesh" |
| 2 | "02" | "network" |
| ... | ... | ... |
| 35 | "0z" | "stable" |
| 36 | "10" | "active" |
| 37 | "11" | "nodes" |
| ... | ... | ... |
| 1295 | "zz" | (last possible) |

### `2char_string` — The Encoded Message

```
"00,01,02,03,04,05,is,07,08,09,0a,0b,0c,in,0d,0e,0f,0g,00,0h,0i,0j"
 ↑  ↑   ↑   ↑   ↑   ↑  ↑   ↑   ↑   ↑   ↑   ↑   ↑  ↑   ↑   ↑   ↑   ↑   ↑   ↑
 │  │   │   │   │   │  │   │   │   │   │   │   │  │   │   │   │   │   │   │
the mesh net has thr nod jar orc and gcp all run sys dae for aut res the gat pro
```

Words ≤2 chars (`is`, `in`) stay in English. All others become 2-char codes, comma-separated.

### `delta_dict` — New Words Only

```python
delta_dict = ["current", "megabytes", "twenty", "four"]  # only NEW words since last message
```

---

## Step-by-Step Protocol

### PHASE 0: One-Time Setup (Before Any Message)

```
0.1  pip install symspellpy          # 80K word dictionary (optional — system works without it)
0.2  pip install nltk                 # Lemmatization (optional — improves compression)
0.3  python3 -c "import nltk; nltk.download('wordnet')"  # one-time download

0.4  Write encoder.py (the script both sides will use)
     → See APPENDIX A for full encoder.py source
```

---

### MESSAGE 1: Session Initialization

```
STEP 1.1 — USER SIDE: Build a.dict₀ from prompt

  a) Take the English prompt:
     "the mesh network has three nodes jarvis oracle and gcp all running systemd daemons for auto restart"

  b) Split into words, lowercase:
     ["the","mesh","network","has","three","nodes","jarvis","oracle","and","gcp",
      "all","running","systemd","daemons","for","auto","restart"]

  c) Build a.dict₀: iterate words left-to-right,
     if word > 2 chars AND word NOT in a.dict₀ → append
     
     a.dict₀ = ["the","mesh","network","has","three","nodes","jarvis","oracle",
                 "and","gcp","all","running","systemd","daemons","auto","restart"]
     (17 entries)

     NOTE: "for" is 3 chars but we keep it — policy is: ≤2 chars = keep as English,
            >2 chars = encode. "for", "and", "the" are >2 chars → they get codes.

  d) Encode prompt to 2char:
     For each word in original prompt:
       if len(word) ≤ 2 → keep as-is
       else → base36_encode(a_dict.index(word))
     
     2char_prompt = "00,01,02,03,04,05,06,07,08,09,0a,0b,0c,0d,0e,0f,0g"
     
     Decodes as: the(00),mesh(01),network(02),has(03),three(04),nodes(05),
                 jarvis(06),oracle(07),and(08),gcp(09),all(0a),running(0b),
                 systemd(0c),daemons(0d),for(0e),auto(0f),restart(0g)

  e) Assemble the message to LLM:
     
     MESSAGE₁ = encoder.py + a.dict₀ + 2char_prompt₁
     
     Example:
     ┌──────────────────────────────────────────┐
     │ [encoder.py source code — 200 chars]     │
     │                                          │
     │ a.dict = ["the","mesh","network","has",  │
     │  "three","nodes","jarvis","oracle",      │
     │  "and","gcp","all","running","systemd",  │
     │  "daemons","auto","restart"]             │
     │                                          │
     │ 00,01,02,03,04,05,06,07,08,09,0a,0b,    │
     │ 0c,0d,0e,0f,0g                           │
     └──────────────────────────────────────────┘

     Total: ~200 (script) + 199 (a.dict) + 47 (2char) = ~446 chars
     vs English prompt: 207 chars
     → Setup cost: 2.1x English (ONE-TIME)


STEP 1.2 — LLM SIDE: Decode and think

  a) LLM receives: encoder.py + a.dict₀ + 2char_prompt₁
  
  b) LLM runs in Python (via terminal/execute_code):
     
     # Load a.dict from the message
     a_dict = ["the","mesh","network","has","three","nodes","jarvis","oracle",
               "and","gcp","all","running","systemd","daemons","auto","restart"]
     
     # Decode the 2char string
     codes = "00,01,02,03,04,05,06,07,08,09,0a,0b,0c,0d,0e,0f,0g".split(",")
     
     english = []
     for code in codes:
         if code[0].isalpha() and len(code) == 1:  # short English word
             english.append(code)
         elif len(code) <= 2 and code.isalnum():
             pos = base36_decode(code)
             english.append(a_dict[pos])
         else:
             english.append(code)  # keep as-is (≤2 char words)
     
     prompt = " ".join(english)
     # → "the mesh network has three nodes jarvis oracle and gcp all running systemd daemons for auto restart"

  c) LLM now has the English prompt in Python memory.
     LLM thinks in English, generates reply:
     
     "all three nodes are currently active jarvis runs on macos with gateway process oracle handles heavy computation on arm ampere gcp handles lightweight polling tasks with only two hundred sixty megabytes free ram counter protocol is stable notion bus has sixty seven active sessions no critical errors in last twenty four hours"


STEP 1.3 — LLM SIDE: Encode reply

  a) Take reply, lowercase, split into words
  
  b) For each word:
       if len(word) ≤ 2 → keep as-is
       else:
         if word in a_dict → get its existing code
         else:
           append word to a_dict
           new_pos = len(a_dict) - 1
           add word to delta_dict
  
  c) Encode reply to 2char using updated a_dict
  
  d) Output: 2char_reply₁ + delta_dict₁
  
     Example output:
     ┌──────────────────────────────────────────┐
     │ 00,04,05,08,0h,0i,0j,06,0k,0l,0m,00,    │
     │ 0n,0o,07,0p,0q,0r,0s,0t,0u,0v,09,0w,    │
     │ 0x,0y,0z,10,11,12,13,14,15,in,16,...     │
     │                                          │
     │ DELTA: ["currently","runs","macos",      │
     │  "gateway","process","handles","heavy",  │
     │  "computation","arm","ampere","lightweight",│
     │  "polling","tasks","only","two","hundred",│
     │  "sixty","megabytes","free","ram",...]   │
     └──────────────────────────────────────────┘

     Output cost: ~173 (2char) + ~250 (delta) = ~423 chars
     vs English reply: ~348 chars
     → Slightly worse on message 1 (~1.2x)


STEP 1.4 — USER SIDE: Update a.dict

  a) Receive: 2char_reply₁ + delta_dict₁
  
  b) Append delta to local a.dict:
     a_dict.extend(delta_dict)
     
     a.dict now has 17 (prompt) + 32 (new reply words) = 49 entries
  
  c) Decode 2char_reply using updated a.dict → read the English reply
```

---

### MESSAGE 2+: Steady State

```
STEP 2.1 — USER SIDE: Encode prompt (NO a.dict, NO script)

  a) Prompt: "what is the current ram usage on gcp"
  
  b) For each word in prompt:
       if len(word) ≤ 2 → keep as-is
       else → base36_encode(a_dict.index(word))
     
     "what" → new word! Append to a.dict locally.
     "is" → ≤2 chars, keep as "is"
     "the" → a_dict.index("the") = 0 → "00"
     "current" → a_dict.index("current") = 17 → "0h"
     "ram" → a_dict.index("ram") = 44 → "1i"
     "usage" → new word! Append. Position 49 → "1n"
     "on" → ≤2 chars, keep as "on"
     "gcp" → a_dict.index("gcp") = 9 → "09"
  
  c) 2char_prompt₂ = "1m,is,00,0h,1i,1n,on,09"
     
     NOTE: New words "what"(1m) and "usage"(1n) are encoded because
     user appended them locally BEFORE sending. They appear in the
     encoded prompt but are NOT sent as delta — the LLM will
     discover them as new and add them to ITS a.dict.

     BUT WAIT — this creates a sync problem! The LLM doesn't know
     "what" = position 49 because the LLM's a.dict stopped at 48.
     
     FIX: User must send delta for new prompt words:
     2char_prompt₂ + DELTA_PROMPT: ["what", "usage"]
     
     OR: User simply sends the 2char with new words marked:
     "+1m,+is,00,0h,1i,+1n,on,09"
     Where "+" prefix = "this is new, append to your a.dict then use the code"
     
     BEST FIX: delta_dict is bidirectional. If prompt has new words,
     send them as delta with the prompt. LLM appends them, then decodes.

  d) Assemble message₂:
     2char_prompt₂ + delta_prompt₂ (if any new words)


STEP 2.2 — LLM SIDE: Decode + think + encode (a.dict already in memory)

  a) LLM receives: 2char_prompt₂ + (optional delta_prompt₂)
  
  b) If delta provided: a_dict.extend(delta_prompt₂)
  
  c) Decode 2char_prompt₂ → English prompt
  
  d) Think in English, generate reply
  
  e) Encode reply: for each word, lookup in a_dict. If new, append + add to delta.
  
  f) Output: 2char_reply₂ + delta_reply₂
  
     OUTPUT cost: ~173 (2char) + ~20 (delta) = ~193 chars
     vs English: ~350 chars
     → 45% SAVINGS ✅


STEP 2.3 — USER SIDE: Update + decode

  a) Append delta_reply₂ to a_dict
  b) Decode 2char_reply₂ → read English reply
```

---

## Capital Letter Handling

```
Rule: Proper nouns (capitalized) get a "C" prefix.

"jarvis" at position 6  → code "06"
"Jarvis" at position 6  → code "C06"

Decoding:
  "C06" → strip "C" → code "06" → a.dict[6] = "jarvis" → capitalize → "Jarvis"
  "06"  → a.dict[6] = "jarvis" → keep lowercase

Zero collision risk. 1 extra char per proper noun (~5% of words in typical text).
```

Why NOT inversion? Inversion (`"06"→"60"`) creates positional ambiguity at scale. Prefix is safer.

---

## Punctuation Handling

```
Punctuation is stripped before encoding, reconstructed contextually.
OR: punctuation preserved as-is in the 2char stream.

Option A (strip punctuation, reconstruct later):
  "nodes? active!" → "nodes","active" → "05,0h" → decoded: "nodes active"
  → Loses punctuation. Fine for agent-to-agent, bad for human-facing.

Option B (preserve punctuation in stream):
  "nodes? active!" → "05? 0h!" → decoded: "nodes? active!"
  → Preserves everything. Punctuation just passes through unencoded.

RECOMMENDED: Option B for human-facing, Option A for agent-to-agent.
```

---

## Token Cost Model

```
╔══════════════════════════════════════════════════════════╗
║                    TOKEN ECONOMICS                       ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  MESSAGE 1 (SETUP):                                      ║
║  INPUT:  script(200) + a.dict₀(199) + 2char(47) = 446   ║
║  OUTPUT: 2char(173) + delta(250) = 423                   ║
║  TOTAL:  869 chars                                       ║
║  ENGLISH: 207 + 348 = 555 chars                          ║
║  COST:    1.6x English (one-time)                        ║
║                                                          ║
║  MESSAGE 2 (STEADY):                                     ║
║  INPUT:  2char(47) + delta_prompt(10) = 57               ║
║  OUTPUT: 2char(173) + delta(50) = 223                    ║
║  TOTAL:  280 chars                                       ║
║  ENGLISH: 555 chars                                      ║
║  COST:    0.50x English → 50% SAVINGS                    ║
║                                                          ║
║  MESSAGE 10 (MATURE):                                    ║
║  INPUT:  2char(47) + delta(5) = 52                       ║
║  OUTPUT: 2char(173) + delta(10) = 183                    ║
║  TOTAL:  235 chars                                       ║
║  ENGLISH: 555 chars                                      ║
║  COST:    0.42x English → 58% SAVINGS                    ║
║                                                          ║
║  SESSION TOTAL (10 messages):                            ║
║  2char total: 869 + (9 × ~250) = 3,119 chars             ║
║  English total: 10 × 555 = 5,550 chars                   ║
║  OVERALL SAVINGS: 44%                                    ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

---

## Python Implementation

### `encoder.py` — The Complete Codec (both sides run this)

```python
"""φ-codec v5 — Session-persistent 2-char base36 word encoder"""
import string

# Base36: 0-9, a-z
CHARS = string.digits + string.ascii_lowercase  # "0123456789abcdefghijklmnopqrstuvwxyz"

def b36_encode(n: int) -> str:
    """Convert integer to 2-char base36 string (padded)."""
    if n == 0:
        return "00"
    result = ""
    while n > 0:
        result = CHARS[n % 36] + result
        n //= 36
    return result.zfill(2)

def b36_decode(code: str) -> int:
    """Convert 2-char base36 string to integer."""
    return CHARS.index(code[0]) * 36 + CHARS.index(code[1])

class Session:
    """Persistent session with a.dict in memory."""
    
    def __init__(self):
        self.a_dict = []  # ordered word list
        self.delta = []   # new words since last message
    
    def load_dict(self, words: list):
        """Initialize a.dict from a word list."""
        self.a_dict = list(words)
        self.delta = []
    
    def encode(self, text: str) -> str:
        """Encode English text to 2char string. Updates a.dict + delta."""
        words = text.lower().replace('.','').replace(',','').replace('?','').replace('!','').split()
        codes = []
        for word in words:
            if len(word) <= 2:
                codes.append(word)  # short word, keep as-is
            elif word[0].isupper():  # (handled before lowercasing)
                # Capital word — handled in calling code before .lower()
                codes.append(word)
            else:
                if word not in self.a_dict:
                    self.a_dict.append(word)
                    self.delta.append(word)
                pos = self.a_dict.index(word)
                codes.append(b36_encode(pos))
        return ','.join(codes)
    
    def decode(self, encoded: str) -> str:
        """Decode 2char string to English text."""
        parts = encoded.split(',')
        words = []
        for part in parts:
            part = part.strip()
            if len(part) <= 2 and all(c in CHARS for c in part) and part.isalnum():
                # It's a 2-char code (or a genuine short word like "is", "on")
                # Try to decode as base36
                try:
                    pos = b36_decode(part)
                    if pos < len(self.a_dict):
                        words.append(self.a_dict[pos])
                    else:
                        words.append(part)  # out of range, treat as literal
                except:
                    words.append(part)  # not valid base36, treat as literal
            else:
                words.append(part)  # literal word
        return ' '.join(words)
    
    def get_delta(self) -> list:
        """Return and clear the delta (new words since last get_delta call)."""
        d = self.delta.copy()
        self.delta = []
        return d


# ── Usage Example ──

if __name__ == "__main__":
    sess = Session()
    
    # Message 1: Setup
    prompt1 = "the mesh network has three nodes jarvis oracle and gcp"
    sess.load_dict(["the","mesh","network","has","three","nodes","jarvis","oracle","and","gcp"])
    
    encoded1 = sess.encode(prompt1)
    delta1 = sess.get_delta()
    print(f"2char: {encoded1}")
    print(f"Delta: {delta1}")
    
    # Decode back
    decoded1 = sess.decode(encoded1)
    print(f"English: {decoded1}")
    
    # Message 2: Steady state (a.dict already in memory)
    reply = "all nodes are active jarvis runs on macos oracle handles heavy computation"
    encoded2 = sess.encode(reply)
    delta2 = sess.get_delta()
    print(f"\n2char reply: {encoded2}")
    print(f"Delta reply: {delta2}")
    
    decoded2 = sess.decode(encoded2)
    print(f"English reply: {decoded2}")
    
    print(f"\na.dict size: {len(sess.a_dict)} words")
```

---

## Session Lifecycle Summary

```
┌──────────────────────────────────────────────────────────────┐
│  STEP  │ USER SIDE              │ LLM SIDE                   │
├────────┼────────────────────────┼────────────────────────────┤
│  SETUP │ pip install symspellpy │ (none needed)              │
│        │ Write encoder.py       │                            │
├────────┼────────────────────────┼────────────────────────────┤
│  MSG 1 │ Build a.dict₀          │ Receive script+a.dict+2char│
│        │ Encode prompt→2char    │ Store a.dict in Python mem │
│        │ Send: script+a.dict+   │ Decode 2char→English       │
│        │       2char_prompt     │ Think in English            │
│        │                        │ Generate reply              │
│        │                        │ Encode reply→2char          │
│        │                        │ Output: 2char+delta        │
│        │ Receive: 2char+delta   │                            │
│        │ Append delta→a.dict    │                            │
│        │ Decode reply→English   │                            │
├────────┼────────────────────────┼────────────────────────────┤
│  MSG 2 │ Encode prompt→2char    │ Receive 2char (+delta)     │
│        │ Send: 2char (+delta)   │ Append delta→a.dict        │
│        │                        │ Decode→English→Think        │
│        │                        │ Encode reply→2char+delta   │
│        │ Receive→append→decode  │                            │
├────────┼────────────────────────┼────────────────────────────┤
│ MSG N  │ (same as MSG 2)        │ (same as MSG 2)            │
│        │ a.dict plateaus ~500   │ a.dict plateaus ~500       │
│        │ Delta shrinks to ~5    │ Delta shrinks to ~5        │
│        │ 50-60% token savings   │ 50-60% token savings       │
└──────────────────────────────────────────────────────────────┘
```
