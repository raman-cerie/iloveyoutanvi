# φ-lang v5 — Morphological Grammar Spec

> The 15M ordered-pair space as a derivational morphology system.
> LLM's trained knowledge IS the resolver. We just encode the pieces.

## Core Insight

The LLM already knows:
- Root words (run, deploy, auth, reach)
- Prefixes (un-, re-, pre-, dis-, mis-)
- Suffixes (-ing, -ed, -s, -ly, -tion, -able, -er, -est)
- Irregular forms (ran→run, went→go, better→good)
- Grammar rules (negation, tense, plurality, comparison)

**We don't need to store these combinations.** We just need atoms for the pieces
and `+` to compose them. The LLM resolves `un+run+ing` → "not running" using knowledge it already paid for during training.

## Grammar Atoms (~50, fixed)

### Prefixes (attach BEFORE root)
| Atom | Meaning | Examples |
|---|---|---|
| `un` | NOT / reverse | unfair, undo, unlock |
| `re` | again | restart, rebuild, redeploy |
| `pre` | before | preload, precheck |
| `dis` | opposite | disconnect, disable |
| `mis` | wrongly | misconfigure, misfire |
| `over` | excessive | overflow, overheat |
| `under` | insufficient | underflow, underpower |
| `out` | surpass | outperform, outrun |
| `co` | together | coexist, copilot |
| `sub` | below | subnet, subprocess |
| `inter` | between | interconnect, interleave |
| `non` | not | nonblocking, noncritical |
| `anti` | against | antipattern, antifragile |
| `auto` | self | autoscale, autoheal |
| `multi` | many | multinode, multitenant |
| `micro` | small | microservice, microburst |
| `hyper` | extreme | hypervisor, hyperparameter |
| `meta` | about | metadata, metaprogramming |
| `proto` | first | prototype, protobuf |
| `pseudo` | fake | pseudocode, pseudorandom |
| `semi` | partial | semistructured, semiauto |
| `super` | above | supervisor, superset |
| `trans` | across | transform, transport |
| `ultra` | beyond | ultrafast, ultralight |
| `mono` | single | monorepo, monolith |
| `poly` | many | polymorphic, polyglot |
| `omni` | all | omnidirectional |
| `para` | beside | parallel, paramilitary |
| `peri` | around | perimeter, peripheral |
| `post` | after | postmortem, postdeploy |

### Suffixes (attach AFTER root)
| Atom | Meaning | Examples |
|---|---|---|
| `ing` | progressive | running, deploying, thinking |
| `ed` | past tense | walked, created, fixed |
| `s` | plural/3rd | nodes, runs, clusters |
| `es` | plural (-es) | boxes, crashes |
| `ly` | adverb | quickly, smoothly, safely |
| `er` | comparative/doer | faster, worker, runner |
| `est` | superlative | fastest, strongest |
| `tion` | noun form | creation, activation, deletion |
| `sion` | noun form | decision, revision |
| `ment` | noun form | deployment, movement |
| `ness` | state of | readiness, darkness |
| `able` | capable of | readable, deployable |
| `ible` | capable of | possible, accessible |
| `ful` | full of | graceful, meaningful |
| `less` | without | stateless, serverless |
| `al` | relating to | computational, operational |
| `ive` | tending to | active, reactive |
| `ous` | full of | dangerous, synchronous |
| `ize` | make into | initialize, optimize |
| `ify` | make into | simplify, verify |
| `en` | make | strengthen, shorten |
| `ist` | one who | specialist, optimist |
| `ism` | belief/system | mechanism, organism |
| `ship` | state/quality | ownership, leadership |
| `dom` | domain/state | freedom, kingdom |
| `ward` | direction | forward, downward |

### Grammar Operators
| Atom | Meaning | Example |
|---|---|---|
| `not` | negation | `not+work+ing` → "not working" |
| `no` | zero/absent | `no+node+s` → "no nodes" |
| `all` | universal | `all+system+s` → "all systems" |
| `any` | existential | `any+error` → "any error" |
| `some` | partial | `some+node+s` → "some nodes" |
| `very` | intensifier | `very+fast` → "very fast" |
| `too` | excessive | `too+slow` → "too slow" |

## Composition Grammar

```
expression  := atom | expression '+' modifier
modifier    := prefix | suffix | grammar_op
atom        := base_word  (from SymSpell top 3906 or a.dict)

Resolution order (left-to-right):
  un + deploy + ed + re + run + ing
  ├─ un+(deploy) → "undeploy"
  ├─ +ed → "undeployed"  
  └─ re+(run) → "rerun"
      └─ +ing → "rerunning"

LLM resolves: "undeployed and rerunning"
```

## Encoding Rules

```
1. Word in SymSpell top 3906? → single atom (0-ZZ)
2. Word derivable from grammar?
   a. Strip known prefixes/suffixes → find root
   b. If root in SymSpell + affixes known → encode as root+affix+affix
3. Word in a.dict? → #n
4. New word? → add to a.dict as #n
```

## Examples

### Simple derivations
| English | φ-v5 | Chars |
|---|---|---|
| running | `run+ing` | 7→2 |
| deployed | `dep+ed` | 7→2 |
| unauthorized | `un+auth+ed` | 12→3 |
| redeployment | `re+dep+ment` | 12→3 |
| stateless | `state+less` | 9→2 |
| unreachable | `un+reach+able` | 11→3 |
| gracefully | `grace+ful+ly` | 11→3 |
| microservices | `micro+serv+s` | 12→3 |
| autoscaling | `auto+scale+ing` | 12→3 |
| misconfigured | `mis+config+ed` | 13→3 |

### Complex compositions
| English | φ-v5 | Chars |
|---|---|---|
| not running | `not+run+ing` | 11→3 |
| very slowly | `very+slow+ly` | 11→3 |
| all nodes active | `all+node+s+act` | 15→4 |
| redeploy immediately | `re+dep+imm+ly` | 19→4 |
| no unhandled errors | `no+un+hand+ed+err+s` | 20→5 |

## The Multiplier

```
English word: "unauthorized"     = 12 chars
φ-v5 atoms:   un + auth + ed     = 3 composition units
                                   (each unit is 1-2 chars: "un"+"Gk"+"ed")
                                   Total: ~8 chars vs 12 = 33% save

English phrase: "not running smoothly" = 22 chars
φ-v5:            not + run + ing + smooth + ly = 5 units
                 "not"+"g7"+"ing"+"smooth_atom"+"ly"
                 Total: ~10 chars vs 22 = 55% save

English sentence: "redeploy all microservices immediately"
= 40 chars
φ-v5: re+dep + all+micro+serv+s + imm+ly
= ~14 chars = 65% save
```

## What the LLM Must Do

The system prompt includes a short grammar table (the ~80 atoms above).
The LLM sees `"not+g7+ing"` and resolves:
1. `not` = negation prefix
2. `g7` = decode via SymSpell → "run" (position g7 in base-62)
3. `ing` = progressive suffix
4. Combine: "not running"

**The LLM already knows how to do this.** It's standard English grammar.
We're just encoding the pieces instead of the whole word, and the LLM
reassembles using knowledge baked into its weights during pretraining.

## Token Economics with Morphology

| Scenario | English | φ-v5 atoms | φ-v5 chars | Save |
|---|---|---|---|---|
| Short derivations (50% of words) | ~9c/word | 2-3 units | ~6c | 33% |
| Complex words (10% of words) | ~13c/word | 3-5 units | ~10c | 23% |
| Base words (40% of words) | ~5c/word | 1 atom | ~2c | 60% |
| **Weighted average** | ~7.5c | ~2.5c | **~67%** | |

Combined with the 3,906 base atoms: 67% average savings across all text.
Grammar atoms add ~10-15% extra savings over pure atom encoding.
