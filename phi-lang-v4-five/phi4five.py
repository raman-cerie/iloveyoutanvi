"""φ-lang v4-five — Session-built dictionary. Token-safe encoding. Delta-only transmission.

Core model:
  Dictionary is BUILT from conversation context — no pre-loaded vocabulary.
  First occurrence: delta carries the word. After that: just the 2-char code.
  Delta → 0 after vocabulary saturation.
  Composition: repeated phrases → 1 series number.
  Language-agnostic: works with any text tokenized by whitespace.
  Token-safe: codes selected so the LLM tokenizer sees 1 code = 1 token.

Zero dependencies. Pure Python stdlib.
"""
import os, json

# ── Token-safe code table (each 2-char code = 1 token under cl100k_base) ──
_CODES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phi4five_codes.json")
with open(_CODES_PATH) as f:
    CODES = json.load(f)  # 274 merge-safe 2-char codes
CODE_COUNT = len(CODES)
C2I = {c: i for i, c in enumerate(CODES)}

def _e(n):
    """Encode integer to 2-char token-safe code."""
    if n < CODE_COUNT:
        return CODES[n]
    return '??'

def _d(c):
    """Decode 2-char code to integer. Returns -1 for unknown codes."""
    return C2I.get(c, -1)


class Communicator:
    """
    Session-built dictionary. No pre-loaded vocabulary.
    
    Every word gets a series number on first use.
    Delta carries the word value when it's new.
    Compositions (repeated 2-4 word phrases) get promoted to single codes.
    Both sides build identical dictionaries from delta.
    """

    CACHE = os.path.expanduser("~/.hermes/phi4five_state.json")

    def __init__(self, load_cache=False):
        self.series = []        # sn → value (str word or list composition)
        self.v2s = {}           # value → sn (reverse lookup)
        self.delta = []         # pending delta: [value, ...]
        self.freq = {}          # composition signature → count
        self.threshold = 3      # promote phrase after 3 occurrences

        if load_cache:
            self.load()

    # ── Value encoding ──

    def _vkey(self, value):
        """Stable string key for a value (word or composition list)."""
        if isinstance(value, list):
            return 'C:' + ','.join(str(x) for x in value)
        return str(value)

    def _resolve(self, value):
        """Resolve a series value to its original text."""
        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            parts = []
            for sn in value:
                if sn < len(self.series) and self.series[sn] is not None:
                    parts.append(self._resolve(self.series[sn]))
            return ' '.join(parts)
        return '?'

    def _assign(self, value):
        """Assign a series number. Returns sn. New entries go to delta."""
        key = self._vkey(value)
        if key in self.v2s:
            return self.v2s[key]
        sn = len(self.series)
        self.series.append(value)
        self.v2s[key] = sn
        self.delta.append(value)
        return sn

    # ── Composition learning ──

    def _learn(self, token_seq):
        """Learn repeated 2-4 token sequences → promote to compositions."""
        n = len(token_seq)
        for length in [4, 3, 2]:
            for i in range(n - length + 1):
                comp = token_seq[i:i + length]
                key = self._vkey(comp)
                self.freq[key] = self.freq.get(key, 0) + 1
                if self.freq[key] >= self.threshold:
                    self._assign(comp)

    # ── Core encode/decode ──

    def encode(self, text):
        """Text → 2-char code stream. Auto-learns phrase compositions."""
        if not text or not text.strip():
            return ''

        words = text.strip().split()
        tokens = []
        for w in words:
            sn = self._assign(w)
            tokens.append(sn)

        self._learn(tokens)

        # Greedy longest-match encoding
        out = []
        i = 0
        while i < len(tokens):
            best_sn, best_len = None, 0

            for comp_key, freq in self.freq.items():
                if freq < self.threshold or not comp_key.startswith('C:'):
                    continue
                try:
                    comp_tokens = [int(x) for x in comp_key[2:].split(',')]
                except ValueError:
                    continue
                clen = len(comp_tokens)
                if i + clen <= len(tokens) and tokens[i:i + clen] == comp_tokens:
                    cvkey = self._vkey(comp_tokens)
                    if cvkey in self.v2s and clen > best_len:
                        best_sn = self.v2s[cvkey]
                        best_len = clen

            if best_sn is not None and best_len >= 2:
                out.append(_e(best_sn))
                i += best_len
            else:
                out.append(_e(tokens[i]))
                i += 1

        return ''.join(out)

    def decode(self, stream):
        """2-char code stream → original text."""
        if not stream:
            return ''

        out = []
        i = 0
        while i < len(stream) - 1:
            code = stream[i:i + 2]
            sn = _d(code)
            if sn >= 0 and sn < len(self.series) and self.series[sn] is not None:
                out.append(self._resolve(self.series[sn]))
            else:
                out.append('?')
            i += 2
        return ' '.join(out)

    # ── Delta sync ──

    def get_delta(self):
        """Return and clear pending delta entries."""
        d = self.delta[:]
        self.delta = []
        return d

    def apply_delta(self, values):
        """Apply received delta to build matching session dictionary."""
        for v in values:
            self._assign(v)

    # ── Persistence ──

    def save(self, path=None):
        """Persist session state to disk."""
        p = path or self.CACHE
        os.makedirs(os.path.dirname(p), exist_ok=True)
        data = {
            'series': self.series,
            'freq': {k: v for k, v in self.freq.items() if v >= self.threshold},
        }
        with open(p, 'w') as f:
            json.dump(data, f)
        return p

    def load(self, path=None):
        """Load persisted session state."""
        p = path or self.CACHE
        if not os.path.exists(p):
            return
        with open(p) as f:
            data = json.load(f)
        self.series = data.get('series', [])
        self.v2s = {}
        for sn, v in enumerate(self.series):
            if v is not None:
                self.v2s[self._vkey(v)] = sn
        self.freq = data.get('freq', {})

    # ── Introspection ──

    def stats(self):
        """Return session statistics."""
        entries = sum(1 for v in self.series if v is not None)
        compositions = sum(1 for v in self.series if isinstance(v, list))
        return {
            'entries': entries,
            'slots': len(self.series),
            'compositions': compositions,
            'delta_pending': len(self.delta),
            'code_space_used': f"{entries}/{CODE_COUNT} ({entries*100//CODE_COUNT}%)",
        }
