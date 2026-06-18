# RS2 Governed AI Agent Demo

**What 32 IETF drafts are trying to specify. RS2 runs it today.**

This repository demonstrates the Risk-Surface Reduction Substrate (RS2) governing a live AI agent — a Claude instance making real decisions, under a formal delegation chain, with every action recorded as an immutable attestation and authority revocable mid-session.

Built on IETF RATS RFC 9334 / RFC 9335. 39 US patents pending — Perkins Coie.

---

## Two Demos

### `atrius_pinn_demo.py` — Physical Infrastructure Governance
Models an ATRIUS PINN node on the SH 130 corridor in Austin, TX as a governed RS2 machine identity (T4). A connected vehicle approaches and requests a session. Six RS2 primitives compose in sequence: Identity → Authority → GovernanceEnvelope → Attestation → LifecycleState → Revocation.

No API key required. Runs entirely on-device.

### `atrius_agent_demo.py` — Governed AI Agent (AT5 Delegation)
ATRIUS delegates governance authority to a Claude AI agent via an RS2 AT5 Delegation Attestation. The agent governs vehicle access on the SH 130 corridor — making real decisions via live API call, with every decision recorded as an immutable AT3 attestation. Agent authority is revoked mid-session. A second vehicle request is blocked by the governance layer without the API ever being called.

Requires an Anthropic API key.

---

## Requirements

- Python 3.10+
- `anthropic` package for the agent demo: `pip install anthropic`
- Anthropic API key for the agent demo

The RS2 primitive stack is included in the `rs2/` directory (stdlib only, no external dependencies).

---

## Run

```bash
# Physical infrastructure demo — no API key needed
python3 atrius_pinn_demo.py

# Governed AI agent demo
export ANTHROPIC_API_KEY="sk-ant-..."
python3 atrius_agent_demo.py
```

---

## What the Agent Demo Proves

```
✓ Principal identity     — ATRIUS as RS2 Authority Object
✓ Agent identity         — Claude as T5 Artifact with DID
✓ AT5 Delegation         — ATRIUS → Claude, scoped + time-bounded
✓ GovernanceEnvelope     — agent session opened with explicit bounds
✓ Live API call          — real Claude decision, governance context injected
✓ AT3 attestation        — agent decision recorded, immutable, non-repudiable
✓ Mid-session revocation — agent authority withdrawn, permanent record
✓ Post-revocation block  — second request blocked without API call
```

An AI agent can be governed at the substrate level.  
Its authority derives from a formal RS2 delegation.  
Every decision is an immutable, authority-attributed attestation.  
Revocation is immediate, non-negotiable, and permanent.  
The governance layer does not depend on the agent's cooperation.

---

## RS2 Stack

| Layer | Component |
|---|---|
| Substrate | RS2 — 10 primitives (Identity, Authority, Attestation AT1–AT5, Conformance, Evaluation, GovernanceEnvelope, Jurisdiction, LifecycleState, PermissionObject, Revocation) |
| Clearinghouse | CH2 — Civix Clearinghouse (issuer-pays, $0.01/event) |
| Settlement | CSS — Clearing Settlement Stack |
| Standard | IETF RATS RFC 9334 / RFC 9335 |

Loquitur — a Liverion Corp. platform / Civix Systems Inc.  
chris@liverion.io · liverion.io
