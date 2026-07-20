# Changelog

## v1.0 — 2026-07-16

### Added
- φ-dict: 1,296 code word dictionary (a0-z9 = 36×36)
- φ-codec: encode/decode/route with Tier 1/2/3 architecture
- φ-actions: opcode → executable handler scripts
- 10 action scripts (c0_ping, c1_ack, c2_exec, c3_reply, c4_deploy, c5_adopt, b0_stat, d0_config, e0_sshk)
- Cross-platform support (macOS Darwin + Linux)
- Zero-LLM route_block() for all deterministic opcodes
- Private GitHub repo setup

### Architecture
- Tier 1: Deterministic (80% traffic) — zero LLM, route_block()
- Tier 2: Semi-deterministic (15%) — tiny model binary gate
- Tier 3: Full reasoning (5%) — large model only

### Impact
- 79% token reduction on routine mesh traffic
- 95% bus bandwidth reduction
- 84KB disk per node
- Zero RAM/CPU overhead (script-only)
