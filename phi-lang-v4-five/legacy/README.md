# φ-lang v4.5

Session-adaptive compression language. SymSpell-backed. Delta-only transmission.

```
pip install symspellpy tiktoken
```

## Architecture

```
2charmax = (series_number, value)

series_number → 2-char code (base62)
value → SymSpell position | raw text | composition [sn1, sn2, ...]

Session dict: sn → value. Both sides build identically from delta.
Delta → 0 after vocabulary saturation.
```

## Files

| File | Purpose |
|------|---------|
| `phi4.5.py` | Core communicator — series numbers, composition RAM |
| `phi4.5_ram.py` | Composition RAM variant — 15M pair space |
| `phi4.5_codes.json` | Token-optimized 2-char code ranking |
| `docs/protocol.md` | Protocol specification |
| `docs/morphology.md` | Grammar atom design |
| `docs/channels.md` | 3-channel protocol |
| `docs/codec.md` | Codec architecture |
| `reference/` | Experimental variants |

## Key Numbers

| Metric | Value |
|--------|-------|
| Character savings | 77% baseline |
| Token savings (phrases) | 60-80% |
| Delta decay | → 0 by message 5-7 |
| SymSpell coverage | 82,834 words |
| Code space | 3,844 2-char codes |

## No dictionary transmission

Both sides run `pip install symspellpy` + identical code → identical dicts.
Only delta (new word positions) flows. After saturation: only 2char codes.
