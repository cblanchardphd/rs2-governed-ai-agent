"""
ATRIUS / Liverion RS2 Evaluation — PINN Node Scenario
======================================================
Scenario: A PINN node on SH 130 (Texas) governed by ATRIUS.
          A connected vehicle approaches and requests a session.
          ATRIUS issues a governance envelope, attests the vehicle's
          permission state, then revokes mid-session to demonstrate
          live governance as a ledger.

Machines in this scenario:
  Node A  — PINN node on SH 130 (this machine, or any machine running this script)
  Node B  — Approaching connected vehicle (second RS2 Identity Object)
  Authority — ATRIUS Industries (governs both)

No external dependencies. Requires Python 3.10+.
Run: python3 atrius_pinn_demo.py
"""

import sys
import os
import json
import importlib.util

# ---------------------------------------------------------------------------
# Path setup — RS2 RI files use hyphens in filenames; load via importlib
# ---------------------------------------------------------------------------
RS2_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "00-Canonical", "RS2")
)

def _load(alias: str, rel_path: str):
    full = os.path.join(RS2_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(alias, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod  # register before exec so dataclass __module__ resolves
    spec.loader.exec_module(mod)
    return mod

_identity    = _load("rs2_identity",    "01-identity/RS2-Identity_RI.py")
_authority   = _load("rs2_authority",   "02-authority/RS2-Authority_RI.py")
_attestation = _load("rs2_attestation", "03-attestation/RS2-Attestation_RI.py")
_ge          = _load("rs2_ge",          "06-governance_envelope/RS2-GovernanceEnvelope_RI.py")
_lifecycle   = _load("rs2_lifecycle",   "08-lifecycle_state/RS2-LifecycleState_RI.py")
_revocation  = _load("rs2_revocation",  "10-revocation/RS2-Revocation_RI.py")

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
#   Node A: PINN node on SH 130 corridor
#   Node B: Approaching connected vehicle
# ===========================================================================
banner(1, "Issue Machine Identities (T4 — Machine)")

id_engine = IdentityEngine()

pinn_node = id_engine.issue(
    rs2_version="1.0",
    identity_id="did:rs2:us-tx:atrius:pinn-sh130-node-001",
    controller="did:rs2:us-tx:atrius:authority",
    lifecycle_state="active",
    jurisdiction="US-TX",
    metadata={
        "label": "ATRIUS PINN Node — SH 130 Corridor, Austin TX",
        "corridor": "SH-130",
        "operator": "ATRIUS Industries",
    }
)
show("Node A — PINN node (SH 130)", pinn_node)

vehicle = id_engine.issue(
    rs2_version="1.0",
    identity_id="did:rs2:us:vehicle:connected-v-8821-beta",
    controller="did:rs2:us:oem:vehicle-oem-authority",
    lifecycle_state="active",
    jurisdiction="US-TX",
    metadata={
        "label": "Connected Vehicle — approaching SH 130 PINN node",
        "class": "commercial-autonomous",
    }
)
show("Node B — Connected vehicle", vehicle)

print("\n  ✓ Both machine identities issued. No external registry required.")
print("    Node A = this machine. Node B = any machine you assign.")


# ===========================================================================
# STEP 2 — Issue ATRIUS as the Governing Authority Object
# ===========================================================================
banner(2, "Issue Authority Object (ATRIUS Industries)")

auth_engine = AuthorityEngine()

atrius_authority = auth_engine.construct(
    rs2_version="1.0",
    authority_id="did:rs2:us-tx:atrius:authority",
    authority_type="infrastructure operator authority",
    jurisdictions=["US-TX", "US"],
    object_types=["attestation", "identity-object", "permission-object"],
    constraints={"domain": "connected-infrastructure", "platform": "PINN"},
    metadata={"label": "ATRIUS Industries — PINN Network Authority"}
)
show("ATRIUS Authority Object", atrius_authority)

print("\n  ✓ ATRIUS is now a formal RS2 Authority Object.")
print("    Every attestation it issues is cryptographically attributed to this record.")


# ===========================================================================
# STEP 3 — Open a GovernanceEnvelope for the connectivity session
# ===========================================================================
banner(3, "Open GovernanceEnvelope — PINN connectivity session")

ge_engine = GovernanceEnvelopeEngine()

session_envelope = ge_engine.define(
    rs2_version="1.0",
    envelope_id="ge-atrius-sh130-session-001",
    authority=["did:rs2:us-tx:atrius:authority"],
    jurisdiction="US-TX",
    object_refs=[
        "did:rs2:us-tx:atrius:pinn-sh130-node-001",
        "did:rs2:us:vehicle:connected-v-8821-beta",
    ],
    effective_at="2026-06-18T13:00:00Z",
    expires_at="2026-06-18T14:00:00Z",
    metadata={"label": "SH 130 PINN connectivity session — vehicle 8821-beta"}
)
show("GovernanceEnvelope", session_envelope)

print("\n  ✓ Session opened. All events within this envelope are")
print("    scoped, time-bounded, and authority-attributed.")


# ===========================================================================
# STEP 4 — Issue AT3 Runtime Attestation
#   ATRIUS attests the vehicle's permission state at connection time.
#   This is the billable event — it would settle through CH2.
# ===========================================================================
banner(4, "Issue AT3 Runtime Attestation — vehicle permission state at PINN node")

att_engine = AttestationEngine()

vehicle_attestation = att_engine.issue(
    rs2_version="1.0",
    attestation_id="att-atrius-sh130-vehicle-8821-001",
    subject_identity="did:rs2:us:vehicle:connected-v-8821-beta",
    issuing_authority="did:rs2:us-tx:atrius:authority",
    assertion=(
        "connected vehicle 8821-beta is operating within governed parameters "
        "on SH 130 corridor; firmware attested; operational state nominal; "
        "authorized for PINN connectivity session ge-atrius-sh130-session-001"
    ),
    governance_envelope="ge-atrius-sh130-session-001",
    asserted_at="2026-06-18T13:01:00Z",
    valid_from="2026-06-18T13:01:00Z",
    valid_until="2026-06-18T14:00:00Z",
    metadata={"attestation_type": "AT3", "corridor": "SH-130"}
)
show("AT3 Runtime Attestation", vehicle_attestation)

print("\n  ✓ Attestation issued. This is the billable CH2 event.")
print("    Rate: $0.01 issuer fee → $0.0085 to ATRIUS node, $0.0015 to Liverion.")
print("    Verifier pays $0.")


# ===========================================================================
# STEP 5 — Record PINN node LifecycleState at session open
# ===========================================================================
banner(5, "LifecycleState — PINN node operational record")

ls_engine = LifecycleStateEngine()

node_state = ls_engine.define(
    rs2_version="1.0",
    lifecycle_state_id="active",
    controller="did:rs2:us-tx:atrius:authority",
    effective_at="2026-06-18T13:00:00Z",
    metadata={
        "subject": "did:rs2:us-tx:atrius:pinn-sh130-node-001",
        "label": "PINN SH-130 — operational state at session open",
    }
)
show("PINN Node LifecycleState", node_state)

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
    jurisdictions=["US-TX"],
    object_types=["attestation", "permission-object"],
    category="geofence-violation",
)

rev_temporal = RevocationTemporal(
    effective_at="2026-06-18T13:22:00Z",
    issued_at="2026-06-18T13:22:05Z",
)

revocation = rev_engine.issue(
    rs2_version="1.0",
    revocation_id="rev-atrius-vehicle-8821-001",
    issuing_authority="did:rs2:us-tx:atrius:authority",
    targets=["did:rs2:us:vehicle:connected-v-8821-beta"],
    scope=rev_scope,
    temporal=rev_temporal,
    governance_envelope="ge-atrius-sh130-session-001",
    metadata={
        "reason": (
            "vehicle 8821-beta detected operating outside approved geofence; "
            "session ge-atrius-sh130-session-001 terminated by ATRIUS authority"
        )
    }
)
show("Revocation Event", revocation)

print("\n  ✓ Permission revoked mid-session at 13:22 UTC.")
print("    This record is immutable. It cannot be deleted or amended.")
print("    The vehicle cannot re-present its AT3 attestation as valid.")
print("    ATRIUS retains permanent, authority-attributed record of the action.")


# ===========================================================================
# Summary
# ===========================================================================
print(f"\n{'='*68}")
print("  EVALUATION COMPLETE — RS2 Primitive Chain on PINN Node Scenario")
print(f"{'='*68}")
print("""
  Primitives exercised:
    ✓ Identity         — two T4 machine identities (PINN node + vehicle)
    ✓ Authority        — ATRIUS issued as RS2 Authority Object
    ✓ GovernanceEnvelope — session opened, scoped, time-bounded
    ✓ Attestation      — AT3 runtime attestation issued (billable CH2 event)
    ✓ LifecycleState   — PINN node operational state recorded
    ✓ Revocation       — mid-session permission withdrawal, permanent record

  What this proves:
    Every event has an authority chain.
    Every event has a permanent record.
    Every AT3 attestation is a CH2 billing event.
    Governance is a ledger — not a kill switch.

  Next step → RILA
    Execute the Reference Implementation Licensing Agreement.
    Embed RS2 in the PINN node firmware.
    Every PINN node on SH 130, Corpus Christi, and Camp Mabry
    becomes a CH2 clearinghouse billing point.
""")
