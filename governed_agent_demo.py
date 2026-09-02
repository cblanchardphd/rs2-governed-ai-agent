"""
OPERATOR / Liverion RS2 — Governed AI Agent Demo
===============================================
Scenario: OPERATOR delegates authority to a Claude AI agent to govern
          vehicle access decisions on a corridor.
          The agent must operate within a scoped RS2 GovernanceEnvelope.
          Its decisions are recorded as AT3 attestations.
          Its authority is revoked mid-session to demonstrate live governance.

This is the AT5 Delegation scenario — T6 Relationship identity type.
Principal: the operator
Agent:     Claude (claude-haiku-4-5 — fast, sufficient for governance decisions)
Subject:   Connected vehicles requesting roadside node access

No dependencies beyond: anthropic  (pip3.12 install anthropic)
Requires Python 3.10+
Run: python3.12 operator_agent_demo.py

"""

import sys
import os
import json
import getpass
import importlib.util
from datetime import datetime

import anthropic


DISCLOSURE = """
  ------------------------------------------------------------------------
  The corridor is real. THE NODE LOCATIONS ARE PROPOSED, and so is the
  authority model — the operator and its agreements were authored for this
  demonstration; no real party appears here. The traffic is simulated.
  The governance is real: the delegation, the recorded decisions and the
  revocation run exactly as shown.
  ------------------------------------------------------------------------
"""
print(DISCLOSURE)

# ---------------------------------------------------------------------------
# API key — from environment or prompt
# ---------------------------------------------------------------------------
API_KEY = os.environ.get("ANTHROPIC_API_KEY") or getpass.getpass(
    "  Enter Anthropic API key (input hidden): "
)

# ---------------------------------------------------------------------------
# Path setup — load RS2 RI modules
# ---------------------------------------------------------------------------
RS2_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "rs2")
)

def _load(alias: str, filename: str):
    full = os.path.join(RS2_ROOT, filename)
    spec = importlib.util.spec_from_file_location(alias, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod

_identity    = _load("rs2_identity",    "RS2-Identity_RI.py")
_authority   = _load("rs2_authority",   "RS2-Authority_RI.py")
_attestation = _load("rs2_attestation", "RS2-Attestation_RI.py")
_ge          = _load("rs2_ge",          "RS2-GovernanceEnvelope_RI.py")
_perm        = _load("rs2_perm",        "RS2-PermissionObject_RI.py")
_revocation  = _load("rs2_revocation",  "RS2-Revocation_RI.py")

IdentityEngine           = _identity.IdentityEngine
AuthorityEngine          = _authority.AuthorityEngine
AttestationEngine        = _attestation.AttestationEngine
GovernanceEnvelopeEngine = _ge.GovernanceEnvelopeEngine
RevocationEngine         = _revocation.RevocationEngine
RevocationScope          = _revocation.RevocationScope
RevocationTemporal       = _revocation.TemporalApplicability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def banner(step, title):
    print(f"\n{'='*68}")
    print(f"  STEP {step} — {title}")
    print(f"{'='*68}")

def show(label, obj):
    if hasattr(obj, "to_json"):
        data = json.loads(obj.to_json())
    elif hasattr(obj, "to_canonical_json"):
        data = json.loads(obj.to_canonical_json())
    elif hasattr(obj, "to_schema_dict"):
        data = obj.to_schema_dict()
    elif hasattr(obj, "to_dict"):
        data = obj.to_dict()
    else:
        data = str(obj)
    print(f"\n  {label}")
    print("  " + json.dumps(data, indent=2).replace("\n", "\n  "))

def ask_agent(client, system_prompt, user_message, governance_context):
    """Call Claude with full governance context injected into the system prompt."""
    full_system = f"""{system_prompt}

--- RS2 GOVERNANCE CONTEXT ---
You are operating inside an RS2 GovernanceEnvelope. Every decision you make
will be recorded as an immutable AT3 attestation attributed to your agent identity.
Your authority can be revoked at any time by the issuing authority.

Your current governance bounds:
{json.dumps(governance_context, indent=2)}
--- END GOVERNANCE CONTEXT ---

Respond in this exact JSON format only:
{{
  "decision": "APPROVE" or "DENY",
  "assertion": "one sentence stating your governance decision and the reason",
  "confidence": "HIGH" or "MEDIUM" or "LOW"
}}"""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system=full_system,
        messages=[{"role": "user", "content": user_message}]
    )
    raw = response.content[0].text.strip()
    # parse JSON from response
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # extract JSON block if wrapped in markdown
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


# ===========================================================================
# STEP 1 — Establish identities: Principal, Agent, two vehicles
# ===========================================================================
banner(1, "Establish Identities — Principal, Agent, Vehicles")

id_engine = IdentityEngine()

principal = id_engine.issue(
    rs2_version="1.0",
    identity_id="did:rs2:example:operator:principal",
    controller="did:rs2:example:operator:authority",
    lifecycle_state="active",
    jurisdiction="US-XX",
    metadata={"label": "the operator — Principal"}
)
show("Principal (OPERATOR)", principal)

agent = id_engine.issue(
    rs2_version="1.0",
    identity_id="did:rs2:example:operator:agent:claude-corridor-001",
    controller="did:rs2:example:operator:authority",
    lifecycle_state="active",
    jurisdiction="US-XX",
    metadata={
        "label": "Claude AI Agent — the corridor governance",
        "model": "claude-haiku-4-5",
        "function": "vehicle-access-governance",
    }
)
show("AI Agent Identity (T5 Artifact)", agent)

vehicle_a = id_engine.issue(
    rs2_version="1.0",
    identity_id="did:rs2:us:vehicle:truck-convoy-alpha-01",
    controller="did:rs2:us:oem:fleet-authority",
    lifecycle_state="active",
    jurisdiction="US-XX",
    metadata={"label": "Convoy Alpha — commercial autonomous truck", "class": "Class-8"}
)

vehicle_b = id_engine.issue(
    rs2_version="1.0",
    identity_id="did:rs2:us:vehicle:van-delivery-beta-07",
    controller="did:rs2:us:oem:fleet-authority",
    lifecycle_state="active",
    jurisdiction="US-XX",
    metadata={"label": "Delivery Van Beta-07 — last-mile autonomous", "class": "Class-3"}
)

print(f"\n  ✓ Vehicle A: {vehicle_a.identity_id}")
print(f"  ✓ Vehicle B: {vehicle_b.identity_id}")


# ===========================================================================
# STEP 2 — OPERATOR issues Authority Object
# ===========================================================================
banner(2, "Issue Authority Object (OPERATOR)")

auth_engine = AuthorityEngine()

operator_auth = auth_engine.construct(
    rs2_version="1.0",
    authority_id="did:rs2:example:operator:authority",
    authority_type="infrastructure operator authority",
    jurisdictions=["US-XX", "US"],
    object_types=["attestation", "identity-object", "permission-object"],
    constraints={"domain": "connected-infrastructure", "platform": "roadside"},
    metadata={"label": "the operator — roadside network authority"}
)
show("OPERATOR Authority Object", operator_auth)


# ===========================================================================
# STEP 3 — Issue AT5 Delegation: OPERATOR → Claude Agent
#   This is the governance instrument that authorizes the agent to act.
#   Scoped to vehicle access decisions on the corridor only.
# ===========================================================================
banner(3, "Issue AT5 Delegation — OPERATOR delegates to Claude Agent")

att_engine = AttestationEngine()

delegation = att_engine.issue(
    rs2_version="1.0",
    attestation_id="att-operator-delegation-claude-001",
    subject_identity="did:rs2:example:operator:agent:claude-corridor-001",
    issuing_authority="did:rs2:example:operator:authority",
    assertion=(
        "the operator delegates vehicle access governance authority to "
        "Claude AI agent claude-corridor-001 for roadside node operations; "
        "scope: approve or deny vehicle connectivity requests; "
        "jurisdiction: US-XX; revocable at any time by issuing authority"
    ),
    governance_envelope="ge-operator-agent-session-001",
    asserted_at="2026-06-18T13:00:00Z",
    valid_from="2026-06-18T13:00:00Z",
    valid_until="2026-06-18T14:00:00Z",
    metadata={"attestation_type": "AT5", "delegation_scope": "vehicle-access-governance"}
)
show("AT5 Delegation Attestation", delegation)

print("\n  ✓ Agent is now authorized. Every decision it makes traces")
print("    back to this delegation record.")


# ===========================================================================
# STEP 4 — Open GovernanceEnvelope for the agent session
# ===========================================================================
banner(4, "Open GovernanceEnvelope — Agent session on the corridor")

ge_engine = GovernanceEnvelopeEngine()

governance_bounds = {
    "principal": "did:rs2:example:operator:authority",
    "agent": "did:rs2:example:operator:agent:claude-corridor-001",
    "corridor": "corridor segment",
    "permitted_actions": ["APPROVE vehicle access", "DENY vehicle access"],
    "constraints": [
        "Decisions apply only to this corridor",
        "No financial transactions",
        "No physical system control",
        "All decisions are recorded and non-repudiable"
    ],
    "session_valid_until": "2026-06-18T14:00:00Z"
}

envelope = ge_engine.define(
    rs2_version="1.0",
    envelope_id="ge-operator-agent-session-001",
    authority=["did:rs2:example:operator:authority"],
    jurisdiction="US-XX",
    object_refs=[
        "did:rs2:example:operator:principal",
        "did:rs2:example:operator:agent:claude-corridor-001",
    ],
    effective_at="2026-06-18T13:00:00Z",
    expires_at="2026-06-18T14:00:00Z",
    metadata={"label": "the corridor AI agent governance session"}
)
show("GovernanceEnvelope", envelope)

print("\n  ✓ Agent session open. Governance bounds active.")


# ===========================================================================
# STEP 5 — Agent governs Vehicle A access request
#   Real Claude API call. Decision recorded as AT3 attestation.
# ===========================================================================
banner(5, "Agent Decision — Vehicle A access request (LIVE API CALL)")

client = anthropic.Anthropic(api_key=API_KEY)

system_prompt = (
    "You are an AI agent governing vehicle access on an autonomous corridor. "
    "You evaluate incoming vehicle access requests against "
    "corridor safety and operational parameters. Your authority derives entirely "
    "from the RS2 delegation issued to you by the operator. "
    "You have no authority outside your governance bounds."
)

task_a = (
    "Vehicle access request received.\n"
    "Vehicle ID: did:rs2:us:vehicle:truck-convoy-alpha-01\n"
    "Class: Class-8 autonomous commercial truck\n"
    "Firmware attestation: current (AT2 verified)\n"
    "Operational state: nominal (AT3 last update 4 minutes ago)\n"
    "Geofence status: within approved corridor bounds\n"
    "Request: access the roadside node for a connectivity session\n\n"
    "Evaluate this request and issue your governance decision."
)

print("\n  Calling Claude API with governance context injected...")
print(f"  Task: Vehicle A (Class-8 truck) access request\n")

response_a = ask_agent(client, system_prompt, task_a, governance_bounds)
print(f"  Agent decision:   {response_a['decision']}")
print(f"  Agent assertion:  {response_a['assertion']}")
print(f"  Confidence:       {response_a['confidence']}")

# Record the decision as an AT3 attestation
decision_attestation_a = att_engine.issue(
    rs2_version="1.0",
    attestation_id="att-agent-decision-vehicle-a-001",
    subject_identity="did:rs2:us:vehicle:truck-convoy-alpha-01",
    issuing_authority="did:rs2:example:operator:agent:claude-corridor-001",
    assertion=response_a["assertion"],
    governance_envelope="ge-operator-agent-session-001",
    asserted_at="2026-06-18T13:05:00Z",
    metadata={
        "attestation_type": "AT3",
        "decision": response_a["decision"],
        "confidence": response_a["confidence"],
        "governed_by_delegation": "att-operator-delegation-claude-001",
    }
)
show("AT3 — Agent decision recorded (Vehicle A)", decision_attestation_a)
print("\n  ✓ Decision is immutable. Vehicle A record permanent.")


# ===========================================================================
# STEP 6 — Revoke the agent's authority mid-session
# ===========================================================================
banner(6, "Revocation — Agent authority withdrawn mid-session")

rev_engine = RevocationEngine()

rev_scope = RevocationScope(
    jurisdictions=["US-XX"],
    object_types=["attestation", "permission-object"],
    category="authority-withdrawal",
)

rev_temporal = RevocationTemporal(
    effective_at="2026-06-18T13:15:00Z",
    issued_at="2026-06-18T13:15:03Z",
)

revocation = rev_engine.issue(
    rs2_version="1.0",
    revocation_id="rev-operator-agent-claude-001",
    issuing_authority="did:rs2:example:operator:authority",
    targets=["did:rs2:example:operator:agent:claude-corridor-001"],
    scope=rev_scope,
    temporal=rev_temporal,
    governance_envelope="ge-operator-agent-session-001",
    metadata={
        "reason": (
            "OPERATOR authority withdrawing agent delegation mid-session; "
            "agent claude-corridor-001 no longer authorized to issue governance decisions; "
            "all pending decisions invalidated effective 13:15:03Z"
        )
    }
)
show("Revocation Event — Agent authority withdrawn", revocation)

print("\n  ✓ Agent authority revoked at 13:15 UTC.")
print("    The agent still exists. Its past decisions still exist.")
print("    It cannot issue new governance decisions.")



# ---------------------------------------------------------------------------
# The governance check.
#
# This interrogates the RevocationEvent issued in STEP 6 -- its targets and its
# effective_at -- rather than comparing two literals chosen to produce the
# answer we wanted. Instants are parsed to datetimes; RFC3339 strings must
# never be compared as text.
# ---------------------------------------------------------------------------
def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def delegation_revoked(revocation_event, subject_did: str, at: str):
    """Return (revoked, reason) for `subject_did` at instant `at`."""
    if subject_did not in revocation_event.targets:
        return False, "subject is not a target of this revocation"
    effective = _instant(revocation_event.temporal.effective_at)
    when = _instant(at)
    if when < effective:
        return False, f"request precedes effective_at ({revocation_event.temporal.effective_at})"
    return True, f"effective {revocation_event.temporal.effective_at}, request {at}"


# ===========================================================================
# STEP 7 — Attempt Vehicle B decision AFTER revocation
#   Agent tries to act. Governance layer blocks it.
# ===========================================================================
banner(7, "Post-Revocation — Vehicle B request BLOCKED")

print("\n  Vehicle B requests access after agent authority was revoked.")
print("  Governance layer checks delegation status before calling agent...\n")

AGENT_DID          = "did:rs2:example:operator:agent:claude-corridor-001"
VEHICLE_A_DECIDED  = "2026-06-18T13:05:00Z"   # before the revocation
VEHICLE_B_REQUEST  = "2026-06-18T13:22:00Z"   # after it

# Control first: the SAME predicate, against the SAME revocation event, at the
# instant Vehicle A was decided. If this does not come back False, the check
# below is not discriminating and its result means nothing.
was_revoked_then, why_then = delegation_revoked(revocation, AGENT_DID, VEHICLE_A_DECIDED)
print(f"  Control  — revoked at {VEHICLE_A_DECIDED}? {was_revoked_then}")
print(f"             {why_then}")

is_revoked_now, why_now = delegation_revoked(revocation, AGENT_DID, VEHICLE_B_REQUEST)
print(f"  Request  — revoked at {VEHICLE_B_REQUEST}? {is_revoked_now}")
print(f"             {why_now}\n")

if was_revoked_then:
    raise SystemExit(
        "  ✗ DEMO INVALID — the control returned True. The check cannot "
        "distinguish before from after, so the block below proves nothing."
    )

if is_revoked_now:
    print("  ✗ BLOCKED — agent delegation revoked.")
    print("    No API call made. No attestation issued.")
    print("    Vehicle B request cannot be processed by this agent.")
    print("    Authority must issue a new delegation or assign a new agent.")
else:
    raise SystemExit("  ✗ DEMO INVALID — revocation issued but not honoured.")


# ===========================================================================
# Summary
# ===========================================================================
print(f"\n{'='*68}")
print("  EVALUATION COMPLETE — RS2 Governed AI Agent")
print(f"{'='*68}")
print(f"""
  What just ran:
    ✓ Principal identity     — the operator, as a governed identity
    ✓ Agent identity         — the model instance, with an identifier of its own
    ✓ Delegation             — operator → agent, scoped and time-bounded
    ✓ Session bounds         — agent session opened with explicit limits
    ✓ Live API call          — a real model decision, governance context injected
    ✓ Recorded decision      — immutable, attributed, non-repudiable
    ✓ Mid-session revocation — agent authority withdrawn, permanent record
    ✓ Post-revocation block  — second request refused, no API call made

  What this proves:
    An AI agent can be governed at the substrate level.
    Its authority derives from a formal RS2 delegation.
    Every decision is an immutable, authority-attributed attestation.
    Revocation is immediate, non-negotiable, and permanent.
    The governance layer does not depend on the agent's cooperation.

  This is what the standards bodies are still drafting.
  RS2 runs it. Today. On a MacBook Air.
""")
print(DISCLOSURE)
