# φ5 — Computational Protocol Specification v1.0

> A token-compact computational substrate for AI context.
> Language-agnostic. Any runtime (Python, JS, C++, Rust) can implement.
> Modes: beacon, cron, chat, session. Not a codec — a virtual machine.

## 1. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      φ5 RUNTIME                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │  a.dict  │   │  b.dict  │   │  c.dict  │   │  stack   │ │
│  │  (ROM)   │   │  (RAM)   │   │ (comment)│   │ (exec)   │ │
│  │  static  │   │ session  │   │  channel │   │  return  │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│                                                              │
│  MODES:  beacon │ cron │ chat │ session                      │
│          one-shot  sched  inter-  stateful                   │
│          no state  persist active  full GC                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 2. Instruction Set

Every instruction is 2 characters. No delimiters needed — the runtime
advances its program counter by 2 chars per cycle.

| Opcode | Name | Operands | Description |
|---|---|---|---|
| `00-ZZ` | LOAD | implicit a.dict index | Push word from static dict to output buffer |
| `#n` | LOADR | b.dict index | Push word from session RAM to output buffer |
| `+xx` | COMPOSE | next atom | Apply function composition (atom+atom) |
| `*nn` | REPEAT | count | Repeat last instruction nn times |
| `!xx` | ENCRYPT | next 2 atoms | Boundary marker for encrypted payload |
| `|xx` | META | next atom | Switch to comment channel for this instruction |
| `=xx` | DEFINE | next atom | Store next atom's value at b.dict[current_slot] |
| `~xx` | FREE | b.dict index | Release b.dict slot (garbage collect) |
| `?nn` | QUERY | result slot | Query LLM: store response at b.dict[nn] |
| `>nn` | EXEC | tool slot | Execute tool at b.dict[nn], store result on stack |

## 3. Dict Architecture

### a.dict — Static ROM (3,906 slots)
- SymSpell top 3,906 words. Immutable.
- 2-char codes 00-ZZ. One code = one English word.
- Shared by all runtimes. Never transmitted.

### b.dict — Session RAM (dynamic slots, indexed #0-#n)
- Mutable. LLM controls via META channel.
- Stores: tools, context, preferences, queries, results.
- `=#n+value` — allocate slot n with value
- `~#n` — free slot n (available for reuse)
- `?nn` — query LLM, store result at slot nn

### c.dict — Comment Channel (parallel to main output)
- Rides on same 2-char stream via `|` prefix
- `|spell?#n+correct` — "did you mean correct?"
- `|error+#n+msg` — "error in slot n: message"
- `|ack` / `|ping` — health check
- `|mode+beacon` — switch runtime mode

## 4. Execution Model

```
CYCLE:
  1. Read 2 chars from input stream (advance pc by 2)
  2. Look up opcode in instruction table
  3. If COMPOSE: read next 2 chars, apply function composition
  4. If META: switch to c.dict, execute instruction there
  5. If REPEAT: replay last instruction nn times
  6. Push result to output buffer or stack
  7. When stream exhausted: flush output buffer → deliver to LLM/user

STATE AFTER EACH CYCLE:
  - pc: current position in atom stream
  - b.dict: current RAM contents
  - stack: return values
  - output_buffer: accumulated output
```

## 5. Mode Configuration

### beacon (one-shot)
- b.dict: empty, no persistence
- After execution: runtime terminates
- Use: status ping, health check, fire-and-forget signal

### cron (scheduled)
- b.dict: loaded from persistent storage
- After execution: b.dict saved to disk
- Use: regular tasks, monitoring, scheduled reports

### chat (interactive)
- b.dict: grows with conversation
- After execution: b.dict retained in memory
- Use: normal conversation, agent interaction

### session (stateful with GC)
- b.dict: full lifecycle management
- LLM controls b.dict via META channel (= and ~ opcodes)
- After execution: b.dict pruned, compacted, retained
- Use: long-running agent sessions, tool orchestration

## 6. Message Format

```
[HEADER: 2 chars] [BODY: N×2 chars]

HEADER:
  b0 — beacon, no b.dict
  c0 — cron, b.dict loaded from path
  h0 — chat, b.dict from memory
  s0 — session, b.dict with GC

BODY:
  Sequence of 2-char atoms. No delimiters.
  Runtime advances pc by 2 per cycle.
  COMPOSE (+xx) reads ONE additional atom (total 4 chars).
  META (|xx) switches channel but same 2-char width.
```

## 7. Reference Implementation Requirements

Any conforming implementation MUST:
1. Accept 2-char fixed-width atom stream as input
2. Maintain a.dict (SymSpell top 3,906 words)
3. Maintain b.dict (mutable session RAM)
4. Implement all opcodes: LOAD, LOADR, COMPOSE, REPEAT, META, DEFINE, FREE, QUERY, EXEC
5. Support all 4 modes: beacon, cron, chat, session
6. Produce 2-char fixed-width atom stream as output
7. Be <= 500 lines in any language

Conforming implementations:
- phi5.py (Python reference, 500 lines)
- phi5.js (JavaScript, for browser agents)
- phi5.rs (Rust, for embedded/high-perf)
- phi5.cpp (C++, for native integrations)

## 8. Why This Isn't a Codec

A codec converts: English ↔ atoms. This converts: computation ↔ atoms.

```
CODEC:    "deploy kubernetes" → "dep+8e" → "deploy kubernetes"
          (compression, 2× roundtrip)

PROTOCOL: "?0+query_status" → LLM executes query → result at b.dict[0]
          → "s0+00+Ml+3G+#0" → LOAD "the", LOAD "mesh", LOAD "network", LOADR #0
          → output: "the mesh network all nodes active"
          (computation, 1× forward execution)
```

The atoms aren't abbreviations. They're instructions. The runtime executes them.
The LLM is a coprocessor accessed via QUERY (?) and EXEC (>) opcodes.
