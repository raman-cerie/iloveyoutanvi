# φ-lang v4-five

Session-built compression codec. Dictionary grows from conversation context — no pre-loaded vocabulary.

**Zero dependencies.** Pure Python stdlib. One file.

```python
from phi4five import Communicator
c = Communicator()
c.encode("hello world")   # → 2-char code stream
c.decode(c.encode(...))   # → original text
```

## How it works

```
First time a word appears → assign 2-char code → delta carries the word
After that               → just the 2-char code
Vocabulary saturates      → delta → 0
Repeated phrases          → promoted to single codes (composition learning)
```

No dictionary is ever pre-loaded or transmitted. Both sides build identical dictionaries from delta.

## Key properties

| Property | Value |
|----------|-------|
| Dependencies | None — pure Python stdlib |
| Code space | 3,844 two-char codes (base62) |
| Language | Agnostic — works with any whitespace-tokenized text |
| Composition | 2-4 word phrases after 3 occurrences |
| Compression | 83%+ for repetitive text, 30% for diverse |
| File | Single `phi4five.py` — 211 lines |

## Usage

```bash
git clone https://github.com/raman-cerie/iloveyoutanvi.git
python3 phi-lang-v4-five/phi4five.py  # that's it
```
