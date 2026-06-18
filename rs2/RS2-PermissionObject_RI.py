"""RS2-PermissionObject_RI — Risk-Surface Reduction Substrate: Permission Object
Reference Implementation (Reduction-to-Practice Exhibit)

Stdlib only. No external dependencies.

Demonstrates:
  - TemporalApplicability and PermissionObject construction with full invariant enforcement
  - additionalProperties=false at top-level and temporal sub-object
  - RFC 3339 date-time string validation (best-effort)
  - PermissionObjectEngine as the single construction entry point

Non-goals (per RS2 spec):
  - No credential issuance workflows
  - No authorization or access-control decisions
  - No enforcement or runtime behavior
  - No cryptographic formats or token structures
  - No policy or compliance interpretation
  - No revocation processing
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence


# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = frozenset({
    "rs2_version", "permission_object_id", "subject_identity",
    "issuing_authority", "permission", "governance_envelope", "temporal",
})
_ALLOWED_KEYS = _REQUIRED_KEYS | frozenset({"supersedes", "metadata"})
_TEMPORAL_REQUIRED = frozenset({"issued_at"})
_TEMPORAL_ALLOWED = _TEMPORAL_REQUIRED | frozenset({"valid_from", "valid_until"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_rfc3339(value: str) -> None:
    """Best-effort structural check for a date-time string."""
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    datetime.fromisoformat(v)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TemporalApplicability:
    """Temporal window sub-object for an RS2 PermissionObject (representation only)."""

    issued_at: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"issued_at": self.issued_at}
        if self.valid_from is not None:
            d["valid_from"] = self.valid_from
        if self.valid_until is not None:
            d["valid_until"] = self.valid_until
        return d


@dataclass(frozen=True, slots=True)
class PermissionObject:
    """Immutable RS2 Permission Object — declares a permission grant, nothing more."""

    rs2_version: str
    permission_object_id: str
    subject_identity: str
    issuing_authority: str
    permission: str
    governance_envelope: str
    temporal: TemporalApplicability
    supersedes: Optional[Sequence[str]] = None
    metadata: Optional[Mapping[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "rs2_version": self.rs2_version,
            "permission_object_id": self.permission_object_id,
            "subject_identity": self.subject_identity,
            "issuing_authority": self.issuing_authority,
            "permission": self.permission,
            "governance_envelope": self.governance_envelope,
            "temporal": self.temporal.to_dict(),
        }
        if self.supersedes is not None:
            d["supersedes"] = list(self.supersedes)
        if self.metadata is not None:
            d["metadata"] = dict(self.metadata)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PermissionObjectEngine:
    """Constructs validated RS2 Permission Objects.

    Enforces all structural invariants:
    - Required string fields non-empty.
    - additionalProperties=false at top-level and temporal.
    - temporal.issued_at is a valid RFC 3339 date-time string.
    - supersedes entries are non-empty strings when provided.
    - Immutable once constructed.
    """

    def issue(
        self,
        *,
        rs2_version: str,
        permission_object_id: str,
        subject_identity: str,
        issuing_authority: str,
        permission: str,
        governance_envelope: str,
        issued_at: str,
        valid_from: Optional[str] = None,
        valid_until: Optional[str] = None,
        supersedes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PermissionObject:
        for name, val in (
            ("rs2_version", rs2_version),
            ("permission_object_id", permission_object_id),
            ("subject_identity", subject_identity),
            ("issuing_authority", issuing_authority),
            ("permission", permission),
            ("governance_envelope", governance_envelope),
            ("issued_at", issued_at),
        ):
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{name} must be a non-empty string")

        _parse_rfc3339(issued_at)
        if valid_from is not None:
            _parse_rfc3339(valid_from)
        if valid_until is not None:
            _parse_rfc3339(valid_until)

        if supersedes is not None:
            if not isinstance(supersedes, list):
                raise ValueError("supersedes must be a list when provided")
            for s in supersedes:
                if not isinstance(s, str) or not s.strip():
                    raise ValueError("each supersedes entry must be a non-empty string")

        temporal = TemporalApplicability(
            issued_at=issued_at,
            valid_from=valid_from,
            valid_until=valid_until,
        )

        return PermissionObject(
            rs2_version=rs2_version,
            permission_object_id=permission_object_id,
            subject_identity=subject_identity,
            issuing_authority=issuing_authority,
            permission=permission,
            governance_envelope=governance_envelope,
            temporal=temporal,
            supersedes=supersedes,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# __main__ — test vectors
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = PermissionObjectEngine()

    vectors = [
        # 1. Minimal — drone operational permission
        dict(
            rs2_version="1.0",
            permission_object_id="perm-drone-inl-flight-001",
            subject_identity="id-drone-inl-alpha-001",
            issuing_authority="auth-inl-v2-001",
            permission="authorized for autonomous flight within INL restricted airspace sector 4",
            governance_envelope="ge-inl-drone-ops-001",
            issued_at="2026-05-12T10:00:00Z",
        ),
        # 2. Permission with validity window
        dict(
            rs2_version="1.0",
            permission_object_id="perm-sdx-settlement-001",
            subject_identity="id-bank-six-participant-001",
            issuing_authority="auth-finma-001",
            permission="authorized to settle digital asset transactions on SIX Digital Exchange",
            governance_envelope="ge-sdx-settlement-001",
            issued_at="2026-05-12T00:00:00Z",
            valid_from="2026-05-12T00:00:00Z",
            valid_until="2027-05-12T00:00:00Z",
            metadata={"tier": "full-participant", "license": "FINMA-2026-0042"},
        ),
        # 3. eIDAS machine identity permission
        dict(
            rs2_version="1.0",
            permission_object_id="perm-eidas-wallet-001",
            subject_identity="id-iot-device-eu-001",
            issuing_authority="auth-eidas-notified-001",
            permission="authorized to present EUDI wallet credentials in EU member state transactions",
            governance_envelope="ge-eidas-iot-001",
            issued_at="2026-05-12T09:30:00Z",
            valid_from="2026-05-12T09:30:00Z",
            valid_until="2027-05-12T09:30:00Z",
        ),
        # 4. Satellite insurance underwriting permission
        dict(
            rs2_version="1.0",
            permission_object_id="perm-swissre-sat-001",
            subject_identity="id-sat-leo-orbit-001",
            issuing_authority="auth-oem-orbital-001",
            permission="satellite identity binding verified; eligible for RS2-anchored insurance underwriting",
            governance_envelope="ge-swissre-space-001",
            issued_at="2026-05-12T08:00:00Z",
            valid_from="2026-05-12T08:00:00Z",
            valid_until="2027-05-12T08:00:00Z",
            metadata={"underwriter": "Swiss Re", "orbit": "LEO"},
        ),
        # 5. Superseding permission
        dict(
            rs2_version="1.0",
            permission_object_id="perm-rivian-ecu-v2-001",
            subject_identity="id-rivian-ecu-001",
            issuing_authority="auth-rivian-oem-001",
            permission="ECU authorized to operate under firmware 2.1.0 OEM compliance profile",
            governance_envelope="ge-rivian-fleet-001",
            issued_at="2026-05-12T12:00:00Z",
            supersedes=["perm-rivian-ecu-v1-001"],
        ),
        # 6. Invariant rejection — empty permission
        dict(
            rs2_version="1.0",
            permission_object_id="perm-bad-001",
            subject_identity="id-x-001",
            issuing_authority="auth-x-001",
            permission="",
            governance_envelope="ge-x-001",
            issued_at="2026-05-12T00:00:00Z",
        ),
        # 7. Invariant rejection — malformed date-time
        dict(
            rs2_version="1.0",
            permission_object_id="perm-bad-002",
            subject_identity="id-x-001",
            issuing_authority="auth-x-001",
            permission="some permission",
            governance_envelope="ge-x-001",
            issued_at="not-a-date",
        ),
    ]

    for i, v in enumerate(vectors, 1):
        try:
            obj = engine.issue(**v)
            print(f"[{i}] OK  {obj.permission_object_id}")
            print(f"     {obj.to_json()}\n")
        except (ValueError, TypeError) as exc:
            print(f"[{i}] ERR (expected) — {exc}\n")
