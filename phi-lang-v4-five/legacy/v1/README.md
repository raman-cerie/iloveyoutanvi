# φ-Lang v1.0 — Mesh Communication Language

**Private repo:** `https://github.com/raman-cerie/phi-lang`  
**Local path:** `~/language/v1/`  
**Dictionary:** 1,296 codes (a0-z9 = 36×36)  
**License:** MIT  

---

## Architecture

```
Message on bus: c0na0 (6 chars)
         ↓
  phi_actions.py decodes opcode → executes handler
         ↓
  ┌──────────────────────────────────────┐
  │  Tier 1 (80%): route_block() → .sh  │ ← zero LLM
  │  Tier 2 (15%): tiny model gate      │ ← ~10 tokens
  │  Tier 3 (5%):  full reasoning       │ ← large model
  └──────────────────────────────────────┘
```

## Quick Start (any node)

```bash
# 1. Auth with GitHub token (from Runtime Config: Raman Github / GH_SATELLITE_TOKEN)
echo "ghp_..." | gh auth login --with-token

# 2. Clone the repo
git clone https://github.com/raman-cerie/phi-lang.git ~/installations/language/
cd ~/installations/language/v1/

# Test installation
python3 scripts/phi_codec.py --test
python3 scripts/phi_dict.py dict | head -5
bash actions/c0_ping.sh Oracle
```

## File Structure

```
~/language/
├── CHANGELOG.md
├── v1/
│   ├── README.md           ← this file
│   ├── dict/
│   │   └── v1.dict         ← master dictionary (a0-z9 = 1,296 codes)
│   ├── scripts/
│   │   ├── phi_codec.py    ← encode/decode/route (zero LLM)
│   │   ├── phi_dict.py     ← dictionary-aware compression
│   │   └── phi_actions.py  ← opcode → executable handler
│   └── actions/
│       ├── c0_ping.sh      ← φping → respond with φpong+stats
│       ├── c1_ack.sh       ← φack → log acknowledgement
│       ├── c2_exec.sh      ← φexec → execute command (Tier 2)
│       ├── c3_reply.sh     ← φreply → post response to bus
│       ├── c4_deploy.sh    ← φdeploy → git pull update (Tier 2)
│       ├── c5_adopt.sh     ← φadopt → confirm protocol
│       ├── b0_stat.sh      ← φstat → full system stats
│       ├── d0_config.sh    ← φconf → read runtime config
│       └── e0_sshk.sh      ← φsshk → share SSH public key
```

## Dictionary

| Code | Word | Code | Word | Code | Word |
|------|------|------|------|------|------|
| a0 | Oracle | b0 | health | c0 | ping |
| a1 | Jarvis | b1 | status | c1 | ack |
| a2 | GCP | b2 | good | c2 | exec |
| a3 | Shiv | b3 | load | c3 | reply |
| d0 | config | e0 | key | f0 | gateway |
| d1 | runtime | e1 | ssh | f1 | mesh |
| g0 | work | h0 | time | i0 | id |

Full dictionary: `~/language/v1/dict/v1.dict`

## Tier System

| Tier | What | Opcodes | LLM | % Traffic |
|------|------|---------|-----|-----------|
| 1 | Deterministic | ping, ack, stat, sshk, rcfg, rply, adopt, cnex, iden, conf, work, health, hb | Zero | 80% |
| 2 | Binary gate | exec, depl, restart | ~10 tokens | 15% |
| 3 | Full reasoning | Novel situations, crisis, architecture | Full model | 5% |

## Usage Examples

```bash
# Encode a message
python3 scripts/phi_codec.py encode φping n=Oracle
# → φping:n=Oracle

# Compress with dictionary
python3 scripts/phi_dict.py compress "φping:n=Oracle"
# → c0na0

# Decode + execute action (zero LLM for Tier 1)
python3 scripts/phi_actions.py exec ping Oracle
# → φpong:n=Oracle,up=1d14h,ld=0.08,mem=1023Mi/7934Mi

# Route auto-response (Tier 1 — zero LLM)
python3 scripts/phi_codec.py route "φping:n=GCP"
# → φpong:n=Oracle,up=OCI_uk-london,phi=v1.0_native
```

## Updates

New dictionary words are posted to the Notion bus:
```
φdict:add=heartbeat,a5
```
All nodes run `git pull` to sync. Commit and push if adding locally.

## Per-Node Checklist

### Oracle (OCI, Ubuntu)
```bash
# Already set up ✅
```

### GCP (Debian)
```bash
# Already set up ✅
```

### Jarvis (macOS)
```bash
# 1. Auth (if not already)
echo "<token_from_runtime_config>" | gh auth login --with-token
# 2. Clone
git clone https://github.com/raman-cerie/phi-lang.git ~/installations/language/
# 3. Test
python3 ~/installations/language/v1/scripts/phi_codec.py --test
# PASS — all scripts are macOS-compatible (Darwin detection)
```

## Token Impact

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Tokens/day (mesh) | 12,800 | 2,640 | 79% |
| Cost/day | $0.00246 | $0.00049 | 80% |
| Bus bandwidth | 48,000 chars | 2,400 chars | 95% |
| Disk | — | 84KB | one-time |
| RAM/CPU | — | 0 | script-only |
