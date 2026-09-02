# Governed AI Agent Demo

**What the standards bodies are still drafting. RS2 runs it today.**

This repository demonstrates the Risk-Surface Reduction Substrate (RS2) governing a live AI agent — a Claude instance making real decisions, under a formal delegation chain, with every action recorded as an immutable attestation and authority revocable mid-session.

Built on IETF RATS (RFC 9334, Remote ATtestation Procedures Architecture, ratified 2023).
U.S. patents pending — Ashurst Perkins Coie.

---

> **What is real here, and what is not.** The corridor is real. **The node locations are
> proposed**, and so is the authority model — the operator, the operating agreements and the
> record-ownership terms were authored for this demonstration, and no real party appears in
> it. The traffic is simulated. **The governance is real:** the delegation, the recorded
> decisions and the revocation run exactly as shown.

---

## Two Demos

### `governed_node_demo.py` — Physical Infrastructure Governance
Models a roadside node on a highway corridor as a governed machine identity. A connected vehicle approaches and requests a session. The operator issues a session, records the vehicle's permission state, then withdraws it mid-session.

No API key required. Runs entirely on-device.

### `governed_agent_demo.py` — Governed AI Agent
An operator delegates governance authority to a Claude AI agent. The agent decides vehicle access — making real decisions via live API call, with every decision recorded as an immutable attestation. Agent authority is then revoked mid-session, and a second vehicle request is blocked by the governance layer **without the API ever being called**.

Requires an Anthropic API key.

---

## Requirements

- Python 3.10+
- `anthropic` package for the agent demo: `pip install anthropic`
- Anthropic API key for the agent demo

The governance code is included in the `rs2/` directory (stdlib only, no external dependencies).

---

## Run

```bash
# Physical infrastructure demo — no API key needed
python3 governed_node_demo.py

# Governed AI agent demo
export ANTHROPIC_API_KEY="sk-ant-..."
python3 governed_agent_demo.py
```

---

## What the Agent Demo Proves

```
✓ Principal identity     — the operator, as a governed identity
✓ Agent identity         — the model instance, with an identifier of its own
✓ Delegation             — operator → agent, scoped and time-bounded
✓ Session bounds         — opened with explicit limits
✓ Live API call          — a real model decision, governance context injected
✓ Recorded decision      — immutable, attributed, non-repudiable
✓ Mid-session revocation — agent authority withdrawn, permanent record
✓ Post-revocation block  — second request refused, no API call made
```

An AI agent can be governed at the substrate level.  
Its authority derives from a formal delegation.  
Every decision is an immutable, authority-attributed record.  
Revocation is immediate, non-negotiable, and permanent.  
The governance layer does not depend on the agent's cooperation.

### How the block is verified

The refusal is not a printed claim. `delegation_revoked()` interrogates the
revocation event issued moments earlier — whether the agent is among its
`targets`, and whether the request instant falls at or after `effective_at`,
both parsed as datetimes rather than compared as strings.

The demo runs that predicate **twice**: once as a control, at the instant the
first vehicle was approved, which must return `False`, and once at the second
vehicle's request time. If the control ever returns `True` the run aborts with
`DEMO INVALID` — a check that cannot tell before from after proves nothing, so
the demo refuses to claim it did.

Both paths are mutation-tested. Point the revocation at a different agent, or
move `effective_at` past the request, and the demo exits non-zero rather than
printing a block it did not earn.

Exactly one `client.messages.create` exists in the file. The blocked request
makes no API call because the revocation says so.

---

Loquitur — a Liverion Corp. platform  
chris@liverion.io · liverion.io
