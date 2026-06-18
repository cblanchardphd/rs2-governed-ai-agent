"""RS2-GovernanceEnvelope_RI — Risk-Surface Reduction Substrate: Governance Envelope
Reference Implementation (Reduction-to-Practice Exhibit)

Stdlib only. No external dependencies.

Demonstrates:
  - AppliesTo, TemporalScope, and GovernanceEnvelope construction with full invariant enforcement
  - authority non-empty list enforcement
  - applies_to.object_refs non-empty list enforcement
  - RFC 3339 date-time string validation (best-effort)
  - additionalProperties=false at top-level and sub-objects
  - GovernanceEnvelopeEngine as the single construction entry point

Non-goals (per RS2 spec):
  - No trust evaluation or policy enforcement
  - No conflict resolution between overlapping envelopes
  - No runtime authorization decisions
  - No enforcement behavior
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = frozenset({
    "rs2_version", "envelope_id", "authority", "jurisdiction", "applies_to", "temporal",
})
_ALLOWED_KEYS = _REQUIRED_KEYS | frozenset({"metadata"})


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
class AppliesTo:
    """Declares which RS2 objects this envelope governs."""

    object_refs: List[str]

    def __post_init__(self) -> None:
        if not isinstance(self.object_refs, list) or not self.object_refs:
            raise ValueError("applies_to.object_refs must be a non-empty list")
        for r in self.object_refs:
            if not isinstance(r, str) or not r.strip():
                raise ValueError("each applies_to.object_refs entry must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        return {"object_refs": list(self.object_refs)}


@dataclass(frozen=True, slots=True)
class TemporalScope:
    """Temporal window for which the governance envelope is effective."""

    effective_at: str
    expires_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.effective_at, str) or not self.effective_at.strip():
            raise ValueError("temporal.effective_at must be a non-empty string")
        _parse_rfc3339(self.effective_at)
        if self.expires_at is not None:
            _parse_rfc3339(self.expires_at)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"effective_at": self.effective_at}
        if self.expires_at is not None:
            d["expires_at"] = self.expires_at
        return d


@dataclass(frozen=True, slots=True)
class GovernanceEnvelope:
    """Immutable RS2 Governance Envelope — defines governance context and authority boundaries."""

    rs2_version: str
    envelope_id: str
    authority: List[str]
    jurisdiction: str
    applies_to: AppliesTo
    temporal: TemporalScope
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "rs2_version": self.rs2_version,
            "envelope_id": self.envelope_id,
            "authority": list(self.authority),
            "jurisdiction": self.jurisdiction,
            "applies_to": self.applies_to.to_dict(),
            "temporal": self.temporal.to_dict(),
        }
        if self.metadata is not None:
            d["metadata"] = dict(self.metadata)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class GovernanceEnvelopeEngine:
    """Constructs validated RS2 Governance Envelope objects.

    Enforces all structural invariants:
    - Required string fields non-empty.
    - authority non-empty list of non-empty strings.
    - applies_to.object_refs non-empty list of non-empty strings.
    - temporal.effective_at is a valid RFC 3339 date-time string.
    - Immutable once constructed.
    """

    def define(
        self,
        *,
        rs2_version: str,
        envelope_id: str,
        authority: List[str],
        jurisdiction: str,
        object_refs: List[str],
        effective_at: str,
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GovernanceEnvelope:
        for name, val in (
            ("rs2_version", rs2_version),
            ("envelope_id", envelope_id),
            ("jurisdiction", jurisdiction),
        ):
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{name} must be a non-empty string")

        if not isinstance(authority, list) or not authority:
            raise ValueError("authority must be a non-empty list")
        for a in authority:
            if not isinstance(a, str) or not a.strip():
                raise ValueError("each authority entry must be a non-empty string")

        applies_to = AppliesTo(object_refs=object_refs)
        temporal = TemporalScope(effective_at=effective_at, expires_at=expires_at)

        return GovernanceEnvelope(
            rs2_version=rs2_version,
            envelope_id=envelope_id,
            authority=authority,
            jurisdiction=jurisdiction,
            applies_to=applies_to,
            temporal=temporal,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# __main__ — test vectors
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = GovernanceEnvelopeEngine()

    vectors = [
        # 1. INL drone operations envelope
        dict(
            rs2_version="1.0",
            envelope_id="ge-inl-drone-ops-001",
            authority=["auth-inl-v2-001"],
            jurisdiction="US-ID",
            object_refs=["id-drone-inl-alpha-001", "att-drone-inl-001"],
            effective_at="2026-05-12T00:00:00Z",
            expires_at="2026-12-31T23:59:59Z",
        ),
        # 2. SIX Digital Exchange settlement envelope
        dict(
            rs2_version="1.0",
            envelope_id="ge-sdx-settlement-001",
            authority=["auth-finma-001", "auth-delegate-sdx-001"],
            jurisdiction="CH",
            object_refs=["id-bank-six-participant-001", "att-sdx-participant-001", "perm-sdx-settlement-001"],
            effective_at="2026-01-01T00:00:00Z",
            metadata={"framework": "SDX-v3", "regulator": "FINMA"},
        ),
        # 3. Swiss Re space insurance envelope
        dict(
            rs2_version="1.0",
            envelope_id="ge-swissre-space-001",
            authority=["auth-oem-orbital-001"],
            jurisdiction="CH",
            object_refs=["id-sat-leo-orbit-001", "att-satellite-swissre-001", "perm-swissre-sat-001"],
            effective_at="2026-05-12T08:00:00Z",
            expires_at="2027-05-12T08:00:00Z",
            metadata={"underwriter": "Swiss Re", "product": "satellite-reinsurance"},
        ),
        # 4. eIDAS multi-jurisdiction envelope
        dict(
            rs2_version="1.0",
            envelope_id="ge-eidas-iot-001",
            authority=["auth-eidas-notified-001"],
            jurisdiction="EU",
            object_refs=["id-iot-device-eu-001", "att-eidas-iot-001", "perm-eidas-wallet-001"],
            effective_at="2026-05-12T09:30:00Z",
            expires_at="2027-05-12T09:30:00Z",
            metadata={"standard": "EUDI-ARF-1.4"},
        ),
        # 5. Rivian fleet envelope — multiple authorities
        dict(
            rs2_version="1.0",
            envelope_id="ge-rivian-fleet-001",
            authority=["auth-rivian-oem-001", "auth-inl-v2-001"],
            jurisdiction="US",
            object_refs=["id-rivian-ecu-001", "att-rivian-ecu-v2-001", "perm-rivian-ecu-v2-001"],
            effective_at="2026-05-12T12:00:00Z",
            metadata={"fleet": "rivian-r1t-pilot", "program": "INL-autonomous-pilot"},
        ),
        # 6. Invariant rejection — empty authority list
        dict(
            rs2_version="1.0",
            envelope_id="ge-bad-001",
            authority=[],
            jurisdiction="US",
            object_refs=["id-x-001"],
            effective_at="2026-05-12T00:00:00Z",
        ),
        # 7. Invariant rejection — empty object_refs
        dict(
            rs2_version="1.0",
            envelope_id="ge-bad-002",
            authority=["auth-x-001"],
            jurisdiction="US",
            object_refs=[],
            effective_at="2026-05-12T00:00:00Z",
        ),
        # 8. Invariant rejection — malformed effective_at
        dict(
            rs2_version="1.0",
            envelope_id="ge-bad-003",
            authority=["auth-x-001"],
            jurisdiction="US",
            object_refs=["id-x-001"],
            effective_at="not-a-date",
        ),
    ]

    for i, v in enumerate(vectors, 1):
        try:
            obj = engine.define(**v)
            print(f"[{i}] OK  {obj.envelope_id}  jurisdiction={obj.jurisdiction}")
            print(f"     {obj.to_json()}\n")
        except (ValueError, TypeError) as exc:
            print(f"[{i}] ERR (expected) — {exc}\n")
