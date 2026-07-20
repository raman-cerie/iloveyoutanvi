# φ-lang Token Cost Analysis: 10s vs 30s Poll Interval

## Baseline: Raw English Mesh Communication
- Avg message: 150 chars → ~50 tokens to process
- Every message must be parsed by LLM

## φ-lang Tier Distribution
| Tier | % Traffic | Tokens | What |
|------|-----------|--------|------|
| 1 | 80% | 0 | Deterministic shell scripts |
| 2 | 15% | ~10 | Tiny model gate check |
| 3 | 5% | ~100 | Full model reasoning |
| **Avg/message** | — | **6.5 tokens** | Weighted average |

## Cost Comparison

| Metric | Raw English | φ-lang 10s | φ-lang 30s |
|--------|-------------|------------|------------|
| Polls/day | 8,640 | 8,640 | 2,880 |
| Msgs/day processed | 8,640 | 8,640 | 2,880 |
| **Tokens/day** | **432,000** | **56,160** | **18,720** |
| Cost/day (cheap model) | $0.086 | $0.011 | $0.004 |
| Cost/day (pro model) | $1.296 | $0.168 | $0.056 |
| Cost/month (pro) | $38.88 | $5.05 | $1.68 |
| **vs Raw** | — | **87% savings** | **96% savings** |

## 10s vs 30s Decision

| Factor | 10s | 30s | Winner |
|--------|-----|-----|--------|
| Monthly cost (pro) | $5.05 | $1.68 | 30s |
| Max latency | 10s | 30s | 10s |
| API calls/month | 2.6M | 864K | 30s |
| Real-time feel | ✅ | ⚠️ | 10s |
| LLM TPM (pro) | 6,480/min | 2,160/min | 30s |
| Risk of rate-limiting | Medium | Low | 30s |

## Cost Utility Score (1-10)
Score = (savings × 0.5) + (responsiveness × 0.3) + (reliability × 0.2)

| Poll | Savings | Responsiveness | Reliability | **Score** |
|------|---------|---------------|-------------|-----------|
| 10s | 87% (8.0) | Real-time (9.0) | Medium (6.0) | **7.9** |
| 30s | 96% (9.5) | Near-time (6.5) | High (9.0) | **8.3** |

**30s wins** — 3× cheaper, better reliability, and for mesh health checks 30s latency is imperceptible. Run with 10s beacon on Tailscale fallback for instant crisis detection.
