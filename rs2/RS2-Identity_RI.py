"""RS2-Identity_RI — Risk-Surface Reduction Substrate: Identity Object
Reference Implementation (Reduction-to-Practice Exhibit)

Stdlib only. No external dependencies.

W3C alignment note:
  The `controller` field corresponds to the W3C DID Core concept of "controller" —
  the entity authorized to govern a DID. RS2 uses this term in place of the
  earlier "governing_authority" to align with W3C DID Core terminology.
  The `identity_id` field should carry a DID URI (e.g. did:rs2:...) in
  W3C-adjacent deployments.

Demonstrates:
  - IdentityObject construction with full invariant enforcement
  - controller (W3C DID-aligned) field enforced as non-empty string
  - Forbidden metadata key detection (permissions / attestations / key material)
  - RFC 3339 date-time validation on created_at (best-effort)
  - IdentityEngine as the single construction entry point

Non-goals (per RS2 spec):
  - No identity issuance procedures or registries
  - No cryptographic key binding
  - No lifecycle transition rules
  - No validation or verification logic beyond structural invariants
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, Optional


# ---------------------------------------------------------------------------
# Invariant constants
# ---------------------------------------------------------------------------

# These fragments are forbidden in metadata keys to enforce the RS2 separability
# invariant: an Identity Object must not embed permissions, attestations, or key
# material. This is not a rejection of W3C vocabulary — it prevents structural
# conflation of identity with other RS2 primitives.
_FORBIDDEN_METADATA_FRAGMENTS: FrozenSet[str] = frozenset({
    # permissions / authority
    "permission", "permissions", "authorize", "authorization",
    "privilege", "grant", "allow", "deny", "role", "policy", "decision",
    # attestations / credentials — must remain separate RS2 primitives
    "attestation", "credential",
    # cryptographic key material — out of scope for RS2 substrate
    "public_key", "private_key", "key_material", "certificate", "x509",
    # factual assertions / provenance
    "provenance", "claim", "assertion", "fact", "truth",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_rfc3339(value: str) -> None:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    datetime.fromisoformat(v)


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class IdentityObject:
    """Immutable RS2 Identity Object — establishes existence and referential continuity.

    Conveys no permissions and asserts no facts beyond existence and referential identity.

    W3C DID alignment:
      identity_id  → DID Subject (the DID URI)
      controller   → DID Controller (W3C DID Core §2.3)
    """

    rs2_version: str
    identity_id: str
    controller: str          # W3C DID Core: controller; formerly governing_authority
    created_at: str
    lifecycle_state: str
    jurisdiction: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "rs2_version": self.rs2_version,
            "identity_id": self.identity_id,
            "controller": self.controller,
            "created_at": self.created_at,
            "lifecycle_state": self.lifecycle_state,
        }
        if self.jurisdiction is not None:
            d["jurisdiction"] = self.jurisdiction
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class IdentityEngine:
    """Constructs validated RS2 Identity Objects.

    Enforces all structural invariants:
    - Required fields non-empty strings.
    - created_at is a valid RFC 3339 date-time string.
    - Forbidden metadata key detection (permissions / attestations / key material).
    - Immutable once constructed.
    """

    def issue(
        self,
        *,
        rs2_version: str,
        identity_id: str,
        controller: str,
        lifecycle_state: str,
        created_at: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IdentityObject:
        ts = created_at or _utc_now_iso()

        for name, val in (
            ("rs2_version", rs2_version),
            ("identity_id", identity_id),
            ("controller", controller),
            ("lifecycle_state", lifecycle_state),
            ("created_at", ts),
        ):
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{name} must be a non-empty string")

        _parse_rfc3339(ts)

        if jurisdiction is not None:
            if not isinstance(jurisdiction, str) or not jurisdiction.strip():
                raise ValueError("jurisdiction must be a non-empty string when provided")

        meta = metadata or {}
        if not isinstance(meta, dict):
            raise ValueError("metadata must be a dict when provided")
        self._check_metadata_invariants(meta)

        return IdentityObject(
            rs2_version=rs2_version,
            identity_id=identity_id,
            controller=controller,
            created_at=ts,
            lifecycle_state=lifecycle_state,
            jurisdiction=jurisdiction,
            metadata=meta,
        )

    @staticmethod
    def _check_metadata_invariants(metadata: Dict[str, Any]) -> None:
        for k in metadata:
            lk = str(k).lower()
            for frag in _FORBIDDEN_METADATA_FRAGMENTS:
                if frag in lk:
                    raise ValueError(
                        f"metadata key '{k}' violates RS2 separability invariant (matched '{frag}')"
                    )


# ---------------------------------------------------------------------------
# __main__ — test vectors
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = IdentityEngine()

    vectors = [
        # 1. INL drone — DID URI identity_id, INL as controller
        dict(
            rs2_version="1.0",
            identity_id="did:rs2:inl:drone-alpha-001",
            controller="did:rs2:inl:authority-v2",
            lifecycle_state="active",
            jurisdiction="US-ID",
            created_at="2026-05-12T10:00:00Z",
            metadata={"label": "INL Drone Alpha — pre-flight identity"},
        ),
        # 2. SIX Digital Exchange participant — Swiss jurisdiction
        dict(
            rs2_version="1.0",
            identity_id="did:rs2:ch:sdx-participant-bank-001",
            controller="did:rs2:ch:finma-authority",
            lifecycle_state="active",
            jurisdiction="CH",
            created_at="2026-01-01T00:00:00Z",
            metadata={"tier": "full-participant", "framework": "SDX-v3"},
        ),
        # 3. Swiss Re satellite — orbital identity
        dict(
            rs2_version="1.0",
            identity_id="did:rs2:space:leo-orbit-sat-001",
            controller="did:rs2:space:oem-orbital-authority",
            lifecycle_state="active",
            jurisdiction="CH",
            created_at="2026-05-12T08:00:00Z",
            metadata={"orbit": "LEO", "underwriter": "Swiss Re"},
        ),
        # 4. eIDAS IoT device — EU jurisdiction
        dict(
            rs2_version="1.0",
            identity_id="did:rs2:eu:iot-device-eidas-001",
            controller="did:rs2:eu:eidas-notified-body",
            lifecycle_state="active",
            jurisdiction="EU",
            created_at="2026-05-12T09:30:00Z",
            metadata={"standard": "EUDI-ARF-1.4"},
        ),
        # 5. Rivian ECU — automotive identity
        dict(
            rs2_version="1.0",
            identity_id="did:rs2:us:rivian-ecu-001",
            controller="did:rs2:us:rivian-oem-authority",
            lifecycle_state="active",
            jurisdiction="US",
            created_at="2026-05-12T12:00:00Z",
            metadata={"platform": "R1T", "component": "ECU"},
        ),
        # 6. Revoked identity
        dict(
            rs2_version="1.0",
            identity_id="did:rs2:us:drone-retired-007",
            controller="did:rs2:inl:authority-v2",
            lifecycle_state="revoked",
            jurisdiction="US-ID",
            created_at="2025-01-01T00:00:00Z",
        ),
        # 7. Invariant rejection — forbidden metadata key (attestation)
        dict(
            rs2_version="1.0",
            identity_id="did:rs2:test:bad-001",
            controller="did:rs2:test:authority",
            lifecycle_state="active",
            created_at="2026-05-12T00:00:00Z",
            metadata={"attestation_ref": "att-123"},
        ),
        # 8. Invariant rejection — empty controller
        dict(
            rs2_version="1.0",
            identity_id="did:rs2:test:bad-002",
            controller="",
            lifecycle_state="active",
            created_at="2026-05-12T00:00:00Z",
        ),
        # 9. Invariant rejection — malformed created_at
        dict(
            rs2_version="1.0",
            identity_id="did:rs2:test:bad-003",
            controller="did:rs2:test:authority",
            lifecycle_state="active",
            created_at="not-a-date",
        ),
    ]

    for i, v in enumerate(vectors, 1):
        try:
            obj = engine.issue(**v)
            print(f"[{i}] OK  {obj.identity_id}  controller={obj.controller}")
            print(f"     {obj.to_json()}\n")
        except (ValueError, TypeError) as exc:
            print(f"[{i}] ERR (expected) — {exc}\n")
