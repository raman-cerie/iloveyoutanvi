"""φ-lang v4 Codec — Encoder/Decoder + Grammar Parser
3-char codes, 46,656 capacity, 20,030 words.
Drop-in replacement for v3 phi_codec.py.

Usage:
    from phi_codec_v4 import Codec
    
    c = Codec()
    c.encode("deploy build test")           # → "c04 b02 r01"
    c.decode("c04 b02 r01")                 # → "deploy build test"
    c.parse("c04?b02>tg ::Oracle")          # → Pipeline AST
    c.execute("c04*3?r01>tg ::Oracle")     # → runs shell commands
"""

import os
import re
import subprocess
import shlex
from typing import Optional

CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789'  # 36 chars
CODE_RE = re.compile(r'^[a-z0-9]{3}$')

# Grammar operators
OPS = {
    'SEQ':   ' ',   # sequential execution
    'COND':  '?',   # conditional: a?b:c (if a succeeds, b; else c)
    'PIPE':  '|',   # pipeline: stdout of a → stdin of b
    'PAR':   ',',   # parallel: run a and b simultaneously
    'RETRY': '*',   # retry: a*3 (run a up to 3 times)
    'NOTIFY': '>',   # notify: a>tg (after a, notify Telegram)
    'TIMEOUT': '@',  # timeout: a@30s (30 second deadline)
    'NODE':   ':',   # node target: a::Oracle (run on Oracle)
    'MODE':   '/',   # mode: a/bg (run in background)
}

# Simple verb-to-action shell script mapping
ACTION_DIRS = [
    os.path.expanduser("~/.hermes/skills"),
    os.path.expanduser("~/installations/language/v1/actions"),
]


class Codec:
    """φ-lang v4 encoder/decoder."""
    
    def __init__(self, dict_path: Optional[str] = None):
        if dict_path is None:
            dict_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "v4.dict"
            )
        
        self.word_to_code = {}  # "deploy" → "c04"
        self.code_to_word = {}  # "c04" → "deploy"
        
        self._load_dict(dict_path)
    
    def _load_dict(self, path: str):
        """Load v4.dict: code=word per line."""
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    code, word = line.split('=', 1)
                    if CODE_RE.match(code):
                        self.code_to_word[code] = word
                        self.word_to_code[word] = code
    
    def encode(self, text: str) -> str:
        """Encode English text to φ-codes.
        
        Example:
            encode("deploy build test") → "c04 c05 c06"
        """
        words = re.findall(r'[a-z0-9]+', text.lower())
        codes = []
        for word in words:
            if word in self.word_to_code:
                codes.append(self.word_to_code[word])
            else:
                # Unknown word: pass through
                codes.append(word)
        return ' '.join(codes)
    
    def decode(self, codes: str) -> str:
        """Decode φ-codes to English text.
        
        Example:
            decode("c04 c05 c06") → "deploy build test"
        """
        tokens = codes.split()
        words = []
        for token in tokens:
            if CODE_RE.match(token) and token in self.code_to_word:
                words.append(self.code_to_word[token])
            else:
                words.append(token)
        return ' '.join(words)
    
    def look_up(self, word: str) -> Optional[str]:
        """Get φ-code for a word."""
        return self.word_to_code.get(word.lower())
    
    def explain(self, code: str) -> Optional[str]:
        """Get English word for a φ-code."""
        return self.code_to_word.get(code)
    
    def compress(self, text: str) -> dict:
        """Compress text to φ-codes, returning stats."""
        original = text
        encoded = self.encode(text)
        orig_chars = len(original)
        enc_chars = len(encoded)
        orig_words = len(original.split())
        enc_tokens = len(encoded.split())
        
        return {
            'original_chars': orig_chars,
            'encoded_chars': enc_chars,
            'ratio': round(enc_chars/orig_chars * 100, 1) if orig_chars else 0,
            'original_words': orig_words,
            'encoded_tokens': enc_tokens,
            'encoded': encoded,
        }


class GrammarParser:
    """Parse φ-lang grammar expressions into executable steps."""
    
    def __init__(self, codec: Codec):
        self.codec = codec
    
    def parse(self, expression: str) -> list:
        """Parse a φ-expression into a pipeline of steps.
        
        Returns list of {op, args, node} steps.
        
        Example:
            parse("c04*3?r01>tg ::Oracle")
            →
            [{op: 'RETRY', action: 'deploy', count: 3, node: 'Oracle'},
             {op: 'COND', then: 'restart', else: None},
             {op: 'NOTIFY', channel: 'tg'}]
        """
        steps = []
        
        # Split on operators
        # c04*3 ? r01 > tg ::Oracle /bg
        tokens = re.split(r'\s+', expression)
        current_node = 'a1'  # default: Jarvis
        
        for token in tokens:
            if not token:
                continue
            
            step = {'op': 'SEQ'}
            
            # Check for node target: ::NodeName
            if '::' in token:
                parts = token.split('::')
                token = parts[0]
                current_node = parts[1]
                step['node'] = current_node
            
            # Check for retry: *N
            if '*' in token:
                parts = token.split('*')
                token = parts[0]
                step['op'] = 'RETRY'
                # Extract just the number from parts[1] (may have trailing operators)
                retry_part = parts[1] if len(parts) > 1 else '3'
                retry_num = re.match(r'\d+', retry_part)
                step['count'] = int(retry_num.group()) if retry_num else 3
                # Put remaining operators back on the token
                remaining = retry_part[retry_num.end():] if retry_num else ''
                if remaining:
                    token = token + remaining
            
            # Check for notify: >channel
            if '>' in token:
                parts = token.split('>')
                token = parts[0]
                step['op'] = 'NOTIFY'
                step['channel'] = parts[1] if len(parts) > 1 else 'tg'
            
            # Check for timeout: @Ns
            if '@' in token:
                parts = token.split('@')
                token = parts[0]
                step['op'] = 'TIMEOUT'
                step['timeout'] = parts[1] if len(parts) > 1 else '30s'
            
            # Check for mode: /bg, /fg
            if '/' in token:
                parts = token.split('/')
                token = parts[0]
                step['mode'] = parts[1] if len(parts) > 1 else 'fg'
            
            # Check for conditional: ?then:else
            if '?' in token:
                parts = token.split('?')
                token = parts[0]
                step['op'] = 'COND'
                if ':' in parts[1]:
                    then_else = parts[1].split(':')
                    step['then'] = then_else[0]
                    step['else'] = then_else[1] if len(then_else) > 1 else None
            
            # Check for pipe: a|b
            if '|' in token:
                parts = token.split('|')
                step['op'] = 'PIPE'
                step['actions'] = parts
            
            # Check for parallel: a,b,c
            if ',' in token:
                parts = token.split(',')
                step['op'] = 'PAR'
                step['actions'] = parts
            
            # Decode the action code
            if CODE_RE.match(token):
                step['action'] = self.codec.decode(token)
            else:
                step['action'] = token
            
            steps.append(step)
        
        return steps
    
    def to_shell(self, steps: list) -> list:
        """Convert parsed steps to shell commands."""
        commands = []
        
        for step in steps:
            node = step.get('node', 'a1')
            mode = step.get('mode', 'fg')
            action = step.get('action', '')
            
            # Build SSH prefix for remote nodes
            prefix = ''
            if node != 'a1':
                # Map node codes to hosts
                node_hosts = {
                    'a0': 'ubuntu@84.8.159.123',  # Oracle
                    'a2': 'shivansh@35.206.121.170',  # GCP
                    'Oracle': 'ubuntu@84.8.159.123',
                    'GCP': 'shivansh@35.206.121.170',
                }
                host = node_hosts.get(node, node)
                prefix = f'ssh -o ConnectTimeout=5 {shlex.quote(host)} '
            
            if step['op'] == 'RETRY':
                count = step.get('count', 3)
                cmd = f'{prefix}retry.sh {action} {count}'
                commands.append(cmd)
            
            elif step['op'] == 'PIPE':
                actions = step.get('actions', [])
                cmd = ' | '.join(f'{prefix}{a}' for a in actions)
                commands.append(cmd)
            
            elif step['op'] == 'PAR':
                actions = step.get('actions', [])
                cmd = ' & '.join(f'{prefix}{a} &' for a in actions)
                commands.append(cmd)
            
            elif step['op'] == 'NOTIFY':
                channel = step.get('channel', 'tg')
                if channel == 'tg':
                    cmd = f'bash actions/v5_notify_tg.sh "{action}"'
                else:
                    cmd = f'echo "["{channel}"] {action}"'
                commands.append(cmd)
            
            elif step['op'] == 'TIMEOUT':
                timeout = step.get('timeout', '30s')
                cmd = f'timeout {timeout} {prefix}{action}'
                commands.append(cmd)
            
            else:  # SEQ or default
                if mode == 'bg':
                    cmd = f'{prefix}nohup {action} &>/dev/null &'
                else:
                    cmd = f'{prefix}{action}'
                commands.append(cmd)
        
        return commands


# ---- Quick CLI ----
if __name__ == '__main__':
    import sys
    
    c = Codec()
    parser = GrammarParser(c)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python phi_codec_v4.py encode 'deploy build test'")
        print("  python phi_codec_v4.py decode 'c04 b02 r01'")
        print("  python phi_codec_v4.py compress 'deploy the scanner to Oracle'")
        print("  python phi_codec_v4.py parse 'c04*3?r01>tg ::Oracle'")
        sys.exit(1)
    
    cmd = sys.argv[1]
    text = sys.argv[2] if len(sys.argv) > 2 else ''
    
    if cmd == 'encode':
        print(c.encode(text))
    elif cmd == 'decode':
        print(c.decode(text))
    elif cmd == 'compress':
        stats = c.compress(text)
        print(f"Original: {stats['original_chars']} chars")
        print(f"Encoded:  {stats['encoded_chars']} chars")
        print(f"Ratio:    {stats['ratio']}%")
        print(f"Output:   {stats['encoded']}")
    elif cmd == 'parse':
        steps = parser.parse(text)
        for i, s in enumerate(steps):
            print(f"  Step {i+1}: {s}")
        cmds = parser.to_shell(steps)
        print("\nShell commands:")
        for cmd in cmds:
            print(f"  $ {cmd}")
