# φ-lang v5 — Three-Channel Protocol

## Channel System

```
main_content | meta_comment

Channel 1 [2charmax]:  Actual message content — atoms resolving to words
Channel 2 [a.dict]:    Session dictionary — embedded in the atom stream
Channel 3 [{comment}]: LLM meta-communication — AFTER the | delimiter
```

`|` is reserved — never appears in atoms (only C62 chars used). If no `|`, no meta.

## Channel 3 — LLM Meta-Communication

### Corrections & Clarifications
| φ-v5 meta | Meaning |
|---|---|
| `\|did-you-mean+atom?` | LLM suggests alternative for previous atom |
| `\|spell?#n+correct_word` | "a.dict entry #n looks like a typo, should be X" |
| `\|clarify+atom` | "what do you mean by this?" |
| `\|more-info+about+atom` | "tell me more about this" |
| `\|confirm?` | "is this correct?" |

### a.dict Management
| φ-v5 meta | Meaning |
|---|---|
| `\|a.dict-del+#n` | Remove a.dict entry #n (typo, obsolete) |
| `\|a.dict-merge+#n+#m` | Entries #n and #m are the same word |
| `\|a.dict-rename+#n+new_word` | Rename entry #n to new_word |
| `\|a.dict-freeze` | Stop adding new entries (vocabulary saturated) |

### Protocol Control
| φ-v5 meta | Meaning |
|---|---|
| `\|reset-session` | Clear a.dict, start fresh |
| `\|upgrade+v6` | Switch to φ-lang v6 protocol |
| `\|compress+full` | Run full compression pass on a.dict |
| `\|ping` | Connection check |
| `\|ack` | Acknowledged / received |

### Agent-to-Agent (pseudo-MCP)
| φ-v5 meta | Meaning |
|---|---|
| `\|exec+tool+args` | Execute tool with arguments |
| `\|result+data` | Tool execution result |
| `\|error+code+msg` | Error with code and message |
| `\|stream+on` / `\|stream+off` | Toggle streaming mode |
| `\|delegate+task+to+agent` | Delegate sub-task to named agent |

## Example Conversations

### Typo autocorrection
```
USER:   0+Ml+3G+7+g7+#0     (sends "the mesh network is runnin" — typo in a.dict)
LLM:    j+FY+atoms...        (responds normally)
        |spell?#0+running    (Channel 3: "a.dict #0 looks like 'runnin', should be 'running'")
USER:   |a.dict-rename+#0+running+ack  (accepts correction)
```
After this exchange: a.dict #0 is renamed from "runnin" to "running". No English wasted.

### Session cleanup
```
LLM:    result+atoms...|a.dict-freeze+a.dict-del+#3+a.dict-del+#7
        ↑                ↑
   Channel 1         Channel 3: "freeze dict, remove entries 3 and 7"
```
LLM detected stale/misspelled entries and prunes them. Zero English overhead.

### Pseudo-MCP relay
```
AGENT A:  chk+euh+now|exec+get_status+--target+all_nodes
AGENT B:  euh+a9z+ok|result+{"nodes":12,"active":12,"latency":"2ms"}
```
Two agents coordinate via φ-v5. Channel 3 carries tool calls and results. No MCP server needed — the grammar IS the protocol.

## Parsing

```python
def parse_message(encoded):
    if '|' in encoded:
        main, meta = encoded.split('|', 1)
        return main, meta
    return encoded, None
```

That's it. `|` is the only addition to the grammar. Channel 3 is empty by default (no `|` = no meta). The overhead: 1 character when meta is present, 0 when absent.
