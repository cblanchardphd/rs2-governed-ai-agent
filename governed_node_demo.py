"""
Liverion RS2 Evaluation — governed roadside node
======================================================
Scenario: A roadside node on a corridor, governed by the operator.
          A connected vehicle approaches and requests a session.
          OPERATOR issues a governance envelope, attests the vehicle's
          permission state, then revokes mid-session to demonstrate
          live governance as a ledger.

Machines in this scenario:
  Node A  — roadside node (this machine, or any machine running this script)
  Node B  — Approaching connected vehicle (second RS2 Identity Object)
  Authority — the operator (governs both)

No external dependencies. Requires Python 3.10+.
Run: python3 governed_node_demo.py

"""

import sys
import os
import json
import importlib.util


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
# Path setup — RS2 RI files use hyphens in filenames; load via importlib
# ---------------------------------------------------------------------------
RS2_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "rs2")
)

def _load(alias: str, filename: str):
    full = os.path.join(RS2_ROOT, filename)
    spec = importlib.util.spec_from_file_location(alias, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod  # register before exec so dataclass __module__ resolves
    spec.loader.exec_module(mod)
    return mod

_identity    = _load("rs2_identity",    "RS2-Identity_RI.py")
_authority   = _load("rs2_authority",   "RS2-Authority_RI.py")
_attestation = _load("rs2_attestation", "RS2-Attestation_RI.py")
_ge          = _load("rs2_ge",          "RS2-GovernanceEnvelope_RI.py")
_lifecycle   = _load("rs2_lifecycle",   "RS2-LifecycleState_RI.py")
_revocation  = _load("rs2_revocation",  "RS2-Revocation_RI.py")

IdentityEngine           = _identity.IdentityEngine
AuthorityEngine          = _authority.AuthorityEngine
AttestationEngine        = _attestation.AttestationEngine
GovernanceEnvelopeEngine = _ge.GovernanceEnvelopeEngine
LifecycleStateEngine     = _lifecycle.LifecycleStateEngine
RevocationEngine         = _revocation.RevocationEngine
RevocationScope          = _revocation.RevocationScope
RevocationTemporal       = _revocation.TemporalApplicability  # revocation's own temporal type


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def banner(step: int, title: str) -> None:
    print(f"\n{'='*68}")
    print(f"  STEP {step} — {title}")
    print(f"{'='*68}")

def show(label: str, obj) -> None:
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


# ===========================================================================
# STEP 1 — Issue Machine Identities (T4)
#   Node A: roadside node
#   Node B: Approaching connected vehicle
# ===========================================================================
banner(1, "Issue Machine Identities")

id_engine = IdentityEngine()

roadside_node = id_engine.issue(
    rs2_version="1.0",
    identity_id="did:rs2:example:operator:roadside-node-001",
    controller="did:rs2:example:operator:authority",
    lifecycle_state="active",
    jurisdiction="US-XX",
    metadata={
        "label": "Roadside node — corridor segment",
        "corridor": "corridor segment",
        "operator": "the operator",
    }
)
show("Node A — roadside node", roadside_node)

vehicle = id_engine.issue(
    rs2_version="1.0",
    identity_id="did:rs2:us:vehicle:connected-v-8821-beta",
    controller="did:rs2:us:oem:vehicle-oem-authority",
    lifecycle_state="active",
    jurisdiction="US-XX",
    metadata={
        "label": "Connected vehicle — approaching the roadside node",
        "class": "commercial-autonomous",
    }
)
show("Node B — Connected vehicle", vehicle)

print("\n  ✓ Both machine identities issued. No external registry required.")
print("    Node A = this machine. Node B = any machine you assign.")


# ===========================================================================
# STEP 2 — Issue OPERATOR as the Governing Authority Object
# ===========================================================================
banner(2, "Issue Authority Object (the operator)")

auth_engine = AuthorityEngine()

operator_authority = auth_engine.construct(
    rs2_version="1.0",
    authority_id="did:rs2:example:operator:authority",
    authority_type="infrastructure operator authority",
    jurisdictions=["US-XX", "US"],
    object_types=["attestation", "identity-object", "permission-object"],
    constraints={"domain": "connected-infrastructure", "platform": "roadside"},
    metadata={"label": "the operator — roadside network authority"}
)
show("OPERATOR Authority Object", operator_authority)

print("\n  ✓ OPERATOR is now a formal issuing authority.")
print("    Every attestation it issues is cryptographically attributed to this record.")


# ===========================================================================
# STEP 3 — Open a GovernanceEnvelope for the connectivity session
# ===========================================================================
banner(3, "Open the session — scoped and time-bounded")

ge_engine = GovernanceEnvelopeEngine()

session_envelope = ge_engine.define(
    rs2_version="1.0",
    envelope_id="ge-operator-corridor-session-001",
    authority=["did:rs2:example:operator:authority"],
    jurisdiction="US-XX",
    object_refs=[
        "did:rs2:example:operator:roadside-node-001",
        "did:rs2:us:vehicle:connected-v-8821-beta",
    ],
    effective_at="2026-06-18T13:00:00Z",
    expires_at="2026-06-18T14:00:00Z",
    metadata={"label": "Roadside connectivity session — vehicle 8821-beta"}
)
show("Session", session_envelope)

print("\n  ✓ Session opened. All events within this envelope are")
print("    scoped, time-bounded, and authority-attributed.")


# ===========================================================================
# STEP 4 — Issue AT3 Runtime Attestation
#   OPERATOR attests the vehicle's permission state at connection time.
#   The attestation is the artifact that outlives the session.
# ===========================================================================
banner(4, "Record the vehicle permission state")

att_engine = AttestationEngine()

vehicle_attestation = att_engine.issue(
    rs2_version="1.0",
    attestation_id="att-operator-corridor-vehicle-8821-001",
    subject_identity="did:rs2:us:vehicle:connected-v-8821-beta",
    issuing_authority="did:rs2:example:operator:authority",
    assertion=(
        "connected vehicle 8821-beta is operating within governed parameters "
        "on the corridor; firmware attested; operational state nominal; "
        "authorized for connectivity session ge-operator-corridor-session-001"
    ),
    governance_envelope="ge-operator-corridor-session-001",
    asserted_at="2026-06-18T13:01:00Z",
    valid_from="2026-06-18T13:01:00Z",
    valid_until="2026-06-18T14:00:00Z",
    metadata={"attestation_type": "AT3", "corridor": "corridor segment"}
)
show("Permission record", vehicle_attestation)

print("\n  ✓ Attestation issued. This is the record that outlives the session.")
print("    It states what was permitted, by whom, and until when.")
print("    Anyone holding it can verify it without asking the issuer.")


# ===========================================================================
# STEP 5 — Record the roadside node state at session open
# ===========================================================================
banner(5, "Record the node operational state")

ls_engine = LifecycleStateEngine()

node_state = ls_engine.define(
    rs2_version="1.0",
    lifecycle_state_id="active",
    controller="did:rs2:example:operator:authority",
    effective_at="2026-06-18T13:00:00Z",
    metadata={
        "subject": "did:rs2:example:operator:roadside-node-001",
        "label": "Roadside node — operational state at session open",
    }
)
show("Node state", node_state)

print("\n  ✓ Node operational state recorded at session open.")
print("    This is the record an insurer or regulator queries at claim time.")


# ===========================================================================
# STEP 6 — Revoke the vehicle's permission mid-session
#   Demonstrates governance as a ledger, not a kill switch.
#   The vehicle detected operating outside approved geofence.
#   The record is permanent and immutable.
# ===========================================================================
banner(6, "Revocation — mid-session permission withdrawal")

rev_engine = RevocationEngine()

rev_scope = RevocationScope(
    jurisdictions=["US-XX"],
    object_types=["attestation", "permission-object"],
    category="geofence-violation",
)

rev_temporal = RevocationTemporal(
    effective_at="2026-06-18T13:22:00Z",
    issued_at="2026-06-18T13:22:05Z",
)

revocation = rev_engine.issue(
    rs2_version="1.0",
    revocation_id="rev-operator-vehicle-8821-001",
    issuing_authority="did:rs2:example:operator:authority",
    targets=["did:rs2:us:vehicle:connected-v-8821-beta"],
    scope=rev_scope,
    temporal=rev_temporal,
    governance_envelope="ge-operator-corridor-session-001",
    metadata={
        "reason": (
            "vehicle 8821-beta detected operating outside approved geofence; "
            "session ge-operator-corridor-session-001 terminated by OPERATOR authority"
        )
    }
)
show("Revocation Event", revocation)

print("\n  ✓ Permission revoked mid-session at 13:22 UTC.")
print("    This record is immutable. It cannot be deleted or amended.")
print("    The vehicle cannot re-present its permission record as valid.")
print("    OPERATOR retains permanent, authority-attributed record of the action.")


# ===========================================================================
# Summary
# ===========================================================================
print(f"\n{'='*68}")
print("  EVALUATION COMPLETE — governed roadside node scenario")
print(f"{'='*68}")
print("""
  What just ran:
    ✓ Identities       — the node and the approaching vehicle, each governed
    ✓ Authority        — the operator, as the issuing authority
    ✓ Session          — opened, scoped, time-bounded
    ✓ Recorded state   — the vehicle's permission state at connection time
    ✓ Node state       — operational status recorded
    ✓ Revocation       — mid-session withdrawal, permanent record

  What this proves:
    Every event has an authority chain.
    Every event has a permanent record.
    Every event is verifiable by someone who was not party to it.
    Governance is a ledger — not a kill switch.

  Next step → Evaluation License Agreement
    Execute the Evaluation License Agreement.
    Embed RS2 in the node firmware.
    Every governed node produces the same record, on the same terms,
    for anyone entitled to read it.
""")
print(DISCLOSURE)
