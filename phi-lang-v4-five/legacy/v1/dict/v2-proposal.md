# φ-Dict v2 — Full Communication Expansion
# Proposal: add 130+ words covering all agent↔agent communication
# Range: a0-z9 = 1,296 codes (36×36). Currently ~60 used.

## New Categories

### Actions (c0-c9) — keep existing, fill gaps
c0=ping       (existing)
c1=ack        (existing)
c2=exec       (existing)
c3=reply      (existing)
c4=deploy     (existing)
c5=adopt      (existing)
c6=verify     (existing)
c7=check      (existing)
c8=request    (existing)
c9=sync       (existing)

### New: Build/Deploy (r0-r9)
r0=build
r1=test
r2=push
r3=pull
r4=merge
r5=branch
r6=commit
r7=rollback
r8=release
r9=restart

### New: Quality/State (s0-s9)  
s0=pass
s1=fail
s2=warn
s3=info
s4=debug
s5=error
s6=critical
s7=stable
s8=unstable
s9=partial

### New: Data Operations (t0-t9)
t0=create
t1=update
t2=delete
t3=read
t4=write
t5=backup
t6=restore
t7=export
t8=import
t9=migrate

### New: Review/Approval (u0-u9)
u0=approve
u1=reject
u2=review
u3=comment
u4=assign
u5=close
u6=reopen
u7=block
u8=unblock
u9=escalate

### New: Communication modes (v0-v9)
v0=broadcast
v1=direct
v2=propose
v3=confirm
v4=deny
v5=notify
v6=alert
v7=remind
v8=report
v9=summarize

### New: System changes (w0-w9)
w0=install
w1=upgrade
w2=downgrade
w3=patch
w4=configure
w5=enable
w6=disable
w7=start
w8=stop
w9=reload

### New: Reasoning/Thinking (x0-x9)
x0=analyze
x1=decide
x2=reason
x3=explain
x4=clarify
x5=question
x6=suggest
x7=recommend
x8=predict
x9=evaluate

### New: Comparison (y0-y9)
y0=better
y1=worse
y2=same
y3=different
y4=increase
y5=decrease
y6=beyond
y7=within
y8=above
y9=below

### New: Priority/Urgency (z0-z9)
z0=urgent
z1=high
z2=medium
z3=low
z4=optional
z5=blocker
z6=quick
z7=background
z8=scheduled
z9=immediate

## Put it all together — agent message now becomes:

Before: "GCP, please review and approve the deployment of phi-lang v2 on Oracle"
After:  "g2u2u0c4k0v2a0,w3"  (13 chars)

That's a 90% compression ratio.
