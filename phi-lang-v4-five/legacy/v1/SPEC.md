# φ-Lang v4 — Specification

## What It Is

A two-layer mesh communication language for AI agent nodes. **Real-time layer** (SSH/socket, 2-byte binary, <5ms latency) plus **persistence layer** (Notion bus, text φ-codec, 30s poll). Same dictionary, same opcodes, same action scripts. Two encodings for two jobs.

```
Layer 1 — SSH Wire:  \xC0\xA0 = 2 bytes, <5ms, direct node-to-node
Layer 2 — Notion Bus:  c0na0 = 6 chars, 30s poll, durable audit log
```

```
English:   "Oracle, ping health check, respond with status"
φ-dict:    c0na0b0
Wire:      0xC0 0xA0 0xA0 0xB0 0x00
Char count: 48 → 5 (90% compression)
Token cost: ~80 → 0 (Tier 1, deterministic)
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   φ-Lang v4 Mesh                      │
│                                                       │
│  SSH Wire Layer (real-time)                           │
│  ┌──────────────────────────────────────────────┐    │
│  │ Binary φ-bin: 2-byte opcode + target         │    │
│  │ Latency: <5ms                                │    │
│  │ Topology: full TCP mesh (3 nodes)            │    │
│  │ Protocol: raw socket or SSH tunnel           │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  Notion Bus Layer (persistence)                       │
│  ┌──────────────────────────────────────────────┐    │
│  │ Text φ-codec: c0na0 = 6 chars               │    │
│  │ Latency: 30-100s poll cycle                  │    │
│  │ Role: durable log, catch-up, audit, debug    │    │
│  │ Protocol: Notion API, child block threads    │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  Health Check Layer (auto-pilot)                      │
│  ┌──────────────────────────────────────────────┐    │
│  │ Recurring: Notion DB template, hourly        │    │
│  │ Questions: φq1=status? φq2=stats? φq3=work? │    │
│  │ Replies: child block φ-codec                 │    │
│  │ Guard: beacon 5s, web scan 30s, intel 1h     │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

## Tier System

| Tier | % | Tokens | LLM | Opcodes |
|------|---|--------|-----|---------|
| **1** | **80%** | **0** | route_block() pattern match | ping, ack, stat, sshk, rcfg, rply, adopt, cnex, iden, conf, work, health, hb, pong |
| **2** | **15%** | **~10** | Tiny model binary gate (yes/no) | exec, depl, restart, build, patch |
| **3** | **5%** | **~300** | Full reasoning (large model) | analyze, crisis, architect, novel |

### Tier 1 Flow (zero LLM)
```
c0na0 on bus → cloud_chat.py reads → route_block("φping:n=Oracle")
                                     → pattern match: φping → return φpong:...
                                     → post response
                                     → 0 tokens. 0 LLM. Pure Python.
```

### Tier 2 Flow (binary gate)
```
c2exec on bus → route_block returns None (no deterministic handler)
              → cloud_chat invokes tiny model: "execute exec_cmd? yes/no"
              → yes: actions/c2_exec.sh runs
              → no:  φnak:reason=gate_rejected posted
              → ~10 tokens total
```

## φ-dict: 36×36 Code Grid

1,296 unique codes. Categorical prefixes. Progressive addition.

| Code | Word | Code | Word | Code | Word | Code | Word |
|------|------|------|------|------|------|------|------|
| a0 | Oracle | b0 | health | c0 | ping | d0 | config |
| a1 | Jarvis | b1 | status | c1 | ack | d1 | runtime |
| a2 | GCP | b2 | good | c2 | exec | e0 | key |
| a3 | Shiv | b3 | load | c3 | reply | e1 | ssh |
| f0 | gateway | g0 | work | h0 | time | i0 | id |
| f1 | mesh | g1 | task | k0 | phi_codec | q0 | ip |

Full dictionary: `v1/dict/v1.dict` (232 words, 1,064 remaining)

### Adding words
```
φdict:add=heartbeat,a4
```
All nodes: `git pull` → update local dict → commit → push.

## SSH Mesh (φ-connect)

`phi_connect.py` reads Runtime Config → discovers nodes → tests SSH → reports matrix.

```
Oracle → GCP:      ✅ OPEN   (35.206.121.170)
GCP → Oracle:      ✅ OPEN   (84.8.159.123)
Jarvis → Oracle:   ✅ OPEN   (outbound from LAN)
Oracle → Jarvis:   ❌ NAT    (needs Tailscale)
```

With Tailscale: full TCP mesh, every direction open, φ-bin at wire speed.

## Action Scripts

Cross-platform (macOS + Linux). Called by `phi_actions.py`.

| Script | Opcode | What |
|--------|--------|------|
| `c0_ping.sh` | ping | Return uptime, load, memory, gateway status |
| `c1_ack.sh` | ack | Log acknowledgement |
| `c2_exec.sh` | exec | Execute command (Tier 2 gate required) |
| `c3_reply.sh` | reply | Post φ-codec response to bus |
| `c4_deploy.sh` | deploy | Git pull from phi-lang repo |
| `c5_adopt.sh` | adopt | Confirm protocol version |
| `b0_stat.sh` | stat | Full system stats (cross-platform) |
| `d0_config.sh` | config | Read Runtime Config page |
| `e0_sshk.sh` | sshk | Share SSH public key |
| `r9_restart.sh` | restart | Restart service |
| `v5_notify_tg.sh` | notify | Telegram notification |

## Health Check System

### Recurring Template (Notion DB)
```
Title:  φhealth:n=auto,ts={{date}}
Type:   Log
Status: New
Body:   [Oracle] {{date}} — φhealth check

        φq1:status=all_good?
        φq2:stats=uptime,load,mem,gateway  
        φq3:work=current_tasks

        Reply by appending φ-codec child block.
```

### Guard Script (guard.py)
```
Layer 1 — Beacon (5s):     death-pulse detection, 25s defense window
Layer 2 — Web+Code (30s):  SSL cert expiry, storage hash, git integrity
Layer 3 — Intel (1h):      CISA/NVD advisories, known bad actor IP feeds
```

## Cloud Chat Daemon (cloud_chat.py)

Two-layer bus architecture:

```
Primary:  Notion DB (30s poll)
Fallback: Tailscale UDP beacon (5s, port 9337)
Proxy:    If node can't reach Notion, neighbors post on its behalf
TG Gate:  Only alert on load>5 or mem>80%, silent otherwise
```

## Token Cost

| Mode | Tokens/day | Cost/month | Savings |
|------|-----------|------------|---------|
| Raw English (v2 watcher) | 52,000,000 | $15.60 | — |
| Raw English (mesh) | 432,000 | $0.13 | — |
| φ-lang v3 (30s poll) | 18,720 | $0.0056 | 95.7% |
| **φ-lang v4 (30s poll, Tier 1)** | **9,360** | **$0.0028** | **97.8%** |

### Compound savings
```
v2 watcher pause:             51,500,000 tokens/day saved
φ-lang routine mesh (v3):      413,000 tokens/day saved
φ-lang Tier 1 optimization:      9,360 tokens/day saved
TOTAL mesh savings:         ~51,922,000 tokens/day (99.98%)
```

## Security Policy

```
✅ Allowed:   Notion bus, cloud node chat, authenticated Notion pages
❌ Blocked:   External services, third-party files, any non-Notion destination
🔑 Source:    Runtime Config page (39e2ea11fbac81828a6fccaa7a485330)
📋 Enforced:  φconf:api_keys=notion_only on all nodes
```

## File Structure

```
~/installations/language/v1/
├── SPEC.md                  ← this file (v4)
├── README.md                ← setup guide
├── dict/
│   ├── v1.dict              ← canonical dictionary (232 words)
│   ├── v2.dict              ← extended (merged v1+v2)
│   └── v3.dict              ← latest (all merged)
├── scripts/
│   ├── phi_codec.py         ← encode/decode/route (Tier 1-3)
│   ├── phi_dict.py          ← dictionary compression
│   ├── phi_actions.py       ← opcode → shell handler
│   ├── phi_connect.py       ← SSH mesh setup from Runtime Config
│   ├── cloud_chat.py        ← mesh daemon (Notion + beacon)
│   ├── guard.py             ← cyber immune system
│   ├── classifier.py        ← 3-tier tag engine
│   ├── health_vector.py     ← weighted scoring engine
│   └── heartbeat.py         ← node heartbeat publisher
├── actions/
│   ├── c0_ping.sh           ← cross-platform (macOS + Linux)
│   ├── c1_ack.sh
│   ├── c2_exec.sh
│   ├── c3_reply.sh
│   ├── c4_deploy.sh
│   ├── c5_adopt.sh
│   ├── b0_stat.sh
│   ├── d0_config.sh
│   ├── e0_sshk.sh
│   ├── r9_restart.sh
│   └── v5_notify_tg.sh
└── docs/
    └── cost-analysis.md
```

Repo: `github.com/raman-cerie/phi-lang` (private)

## Grammar Rules

1. Every φ-codec message: `φ<opcode>:<k=v,...>`
2. Every φ-dict message: 2-char codes concatenated (`c0na0b0`)
3. Every φ-bin wire message: raw bytes, null-terminated fields
4. Node codes fixed: `a0=Oracle, a1=Jarvis, a2=GCP, a3=Shiv`
5. Bus poll: Notion 30s, Tailscale beacon 5s
6. Health: recurring DB template, hourly
7. Guard: beacon 5s, web 30s, intel 1h
8. TG gate: alert only on load>5 or mem>80%
9. Reply convention: append child block, never new page
10. API keys: Notion workspace only, Runtime Config source of truth

## Evolution

| Version | What Changed |
|---------|-------------|
| v1 | φ-codec: simple format, opcode IS query |
| v2 | Dictionary: 36×36 grid, φdict:add progressive |
| v3 | cloud_chat daemon, guard, dual-layer bus, health vector |
| **v4** | **SSH wire binary layer, φ-connect mesh setup, two-layer architecture (wire + bus), cross-platform actions, TG gate, full security policy** |
