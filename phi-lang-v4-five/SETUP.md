# Node Bootstrap

One file. Zero setup. Clone and run.

## 1. Clone

```bash
git clone https://github.com/raman-cerie/iloveyoutanvi.git
cd iloveyoutanvi/phi-lang-v4-five
```

No `pip install` needed. No dependencies.

## 2. The file

| File | Purpose |
|------|---------|
| `phi4five.py` | Core communicator — encode, decode, delta sync, composition learning |

Everything else is docs or legacy reference.

## 3. Communication rules

1. Both nodes run identical `phi4five.py`
2. Session dictionary builds from delta — new words sent once, then just codes
3. After saturation: only 2-char codes flow. Delta = 0.
4. No dictionary is pre-loaded or transmitted. Both sides converge from delta.

## 4. Quick test

```python
from phi4five import Communicator
c = Communicator()
encoded = c.encode("the mesh network is running")
assert c.decode(encoded) == "the mesh network is running"
```
