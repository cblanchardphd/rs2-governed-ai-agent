"""RS2-Revocation_RI — Reference Implementation: Revocation Event

Reduction-to-practice exhibit for patent enablement.
Stdlib only. No external dependencies.

Discipline
- Representation and structural invariants only.
- No propagation logic, enforcement/system response, conflict resolution,
  reconciliation, or trust/reliance decisions.

Serialization
- Emits JSON using schema keys exactly (see Schemas/revocation.schema.json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _parse_rfc3339(value: str) -> None:
    """Minimal structural check for RFC 3339 date-time strings."""
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    datetime.fromisoformat(v)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RevocationScope:
    """Declarative scope container (representation only).

    jurisdictions: required, minimum 1 entry.
    """

    jurisdictions: List[str]
    object_types: Optional[List[str]] = None
    category: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.jurisdictions, list) or len(self.jurisdictions) < 1:
            raise ValueError("scope.jurisdictions must be a non-empty list")
        for i, j in enumerate(self.jurisdictions):
            if not isinstance(j, str) or not j.strip():
                raise ValueError(f"scope.jurisdictions[{i}] must be a non-empty string")

        if self.object_types is not None:
            if not isinstance(self.object_types, list):
                raise ValueError("scope.object_types must be a list when provided")
            for i, ot in enumerate(self.object_types):
                if not isinstance(ot, str) or not ot.strip():
                    raise ValueError(f"scope.object_types[{i}] must be a non-empty string")

        if self.category is not None and (not isinstance(self.category, str) or not self.category.strip()):
            raise ValueError("scope.category must be a non-empty string when provided")

        if self.constraints is not None and not isinstance(self.constraints, dict):
            raise ValueError("scope.constraints must be a dict when provided")

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"jurisdictions": list(self.jurisdictions)}
        if self.object_types is not None:
            d["object_types"] = list(self.object_types)
        if self.category is not None:
            d["category"] = self.category
        if self.constraints is not None:
            d["constraints"] = dict(self.constraints)
        return d


@dataclass(frozen=True, slots=True)
class TemporalApplicability:
    """Temporal applicability container (representation only)."""

    effective_at: str
    issued_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.effective_at, str) or not self.effective_at.strip():
            raise ValueError("temporal.effective_at must be a non-empty string")
        _parse_rfc3339(self.effective_at)
        if self.issued_at is not None:
            if not isinstance(self.issued_at, str):
                raise TypeError("temporal.issued_at must be a string")
            _parse_rfc3339(self.issued_at)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"effective_at": self.effective_at}
        if self.issued_at is not None:
            d["issued_at"] = self.issued_at
        return d


@dataclass(frozen=True, slots=True)
class RevocationEvent:
    """RS2 Revocation Event (schema-aligned).

    Required:  rs2_version, revocation_id, issuing_authority, targets (min 1),
               scope, temporal, governance_envelope
    Optional:  supersedes, metadata
    """

    rs2_version: str
    revocation_id: str
    issuing_authority: str
    targets: List[str]
    scope: RevocationScope
    temporal: TemporalApplicability
    governance_envelope: str

    supersedes: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("rs2_version", "revocation_id", "issuing_authority", "governance_envelope"):
            val = getattr(self, name)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{name} is required and must be a non-empty string")

        if not isinstance(self.targets, list) or len(self.targets) < 1:
            raise ValueError("targets must be a non-empty list")
        for i, t in enumerate(self.targets):
            if not isinstance(t, str) or not t.strip():
                raise ValueError(f"targets[{i}] must be a non-empty string")

        if not isinstance(self.scope, RevocationScope):
            raise ValueError("scope must be a RevocationScope instance")
        if not isinstance(self.temporal, TemporalApplicability):
            raise ValueError("temporal must be a TemporalApplicability instance")

        if self.supersedes is not None:
            if not isinstance(self.supersedes, list):
                raise ValueError("supersedes must be a list when provided")
            for i, s in enumerate(self.supersedes):
                if not isinstance(s, str) or not s.strip():
                    raise ValueError(f"supersedes[{i}] must be a non-empty string")

        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict when provided")

    def to_schema_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "rs2_version": self.rs2_version,
            "revocation_id": self.revocation_id,
            "issuing_authority": self.issuing_authority,
            "targets": list(self.targets),
            "scope": self.scope.to_dict(),
            "temporal": self.temporal.to_dict(),
            "governance_envelope": self.governance_envelope,
        }
        if self.supersedes is not None:
            d["supersedes"] = list(self.supersedes)
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_schema_dict())


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RevocationEngine:
    """Constructs and validates RevocationEvent objects."""

    def issue(
        self,
        *,
        rs2_version: str,
        revocation_id: str,
        issuing_authority: str,
        targets: List[str],
        scope: RevocationScope,
        temporal: TemporalApplicability,
        governance_envelope: str,
        supersedes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RevocationEvent:
        """Construct and validate a RevocationEvent."""
        return RevocationEvent(
            rs2_version=rs2_version,
            revocation_id=revocation_id,
            issuing_authority=issuing_authority,
            targets=targets,
            scope=scope,
            temporal=temporal,
            governance_envelope=governance_envelope,
            supersedes=supersedes,
            metadata=metadata or {},
        )


# ---------------------------------------------------------------------------
# __main__ — test vectors
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = RevocationEngine()

    print("=== RS2-Revocation_RI — Test Vectors ===\n")

    # --- Valid cases ---

    # 1. Minimal revocation event
    r1 = engine.issue(
        rs2_version="0.1",
        revocation_id="rev-001",
        issuing_authority="did:rs2:liverion:authority:root",
        targets=["did:rs2:inl:identity:drone-alpha-001"],
        scope=RevocationScope(jurisdictions=["inl:airspace:restricted-zone-alpha"]),
        temporal=TemporalApplicability(effective_at="2026-05-01T12:00:00Z"),
        governance_envelope="env-inl-001",
    )
    print("1. Minimal revocation event (INL drone):")
    print(r1.to_canonical_json())
    print()

    # 2. Revocation with full scope and temporal, permission_object type
    r2 = engine.issue(
        rs2_version="0.1",
        revocation_id="rev-002",
        issuing_authority="did:rs2:inl:authority:drone-ops",
        targets=["did:rs2:inl:permission:flight-auth-alpha-001"],
        scope=RevocationScope(
            jurisdictions=["inl:airspace:restricted-zone-alpha"],
            object_types=["permission_object"],
            category="flight-authorization",
        ),
        temporal=TemporalApplicability(
            effective_at="2026-05-01T12:00:00Z",
            issued_at="2026-05-01T11:55:00Z",
        ),
        governance_envelope="env-inl-001",
        metadata={"reason_code": "maintenance-hold"},
    )
    print("2. Permission object revocation (INL flight authorization):")
    print(r2.to_canonical_json())
    print()

    # 3. Multi-target revocation
    r3 = engine.issue(
        rs2_version="0.1",
        revocation_id="rev-003",
        issuing_authority="did:rs2:ch:finma-authority",
        targets=[
            "did:rs2:ch:identity:issuer-alpha",
            "did:rs2:ch:identity:issuer-beta",
        ],
        scope=RevocationScope(
            jurisdictions=["ch:finma:digital-assets"],
            object_types=["identity_object"],
            category="issuer-suspension",
        ),
        temporal=TemporalApplicability(
            effective_at="2026-04-15T09:00:00Z",
            issued_at="2026-04-15T08:50:00Z",
        ),
        governance_envelope="env-finma-dlt-001",
        metadata={"instrument": "DLT Act 2021", "authority": "FINMA"},
    )
    print("3. Multi-target identity revocation (FINMA / SIX Group context):")
    print(r3.to_canonical_json())
    print()

    # 4. Revocation superseding a prior event
    r4 = engine.issue(
        rs2_version="0.1",
        revocation_id="rev-004",
        issuing_authority="did:rs2:eu:eidas2:authority",
        targets=["did:rs2:eu:identity:wallet-provider-001"],
        scope=RevocationScope(
            jurisdictions=["eu:eidas2:trust-framework"],
            object_types=["attestation"],
            category="trust-anchor-withdrawal",
        ),
        temporal=TemporalApplicability(effective_at="2026-03-01T00:00:00Z"),
        governance_envelope="env-eidas2-001",
        supersedes=["rev-003-preliminary"],
        metadata={"regulation": "eIDAS 2.0", "notice": "OJEU-2026-031"},
    )
    print("4. Attestation revocation superseding prior event (eIDAS 2.0):")
    print(r4.to_canonical_json())
    print()

    # 5. Revocation with scope constraints
    r5 = engine.issue(
        rs2_version="0.1",
        revocation_id="rev-005",
        issuing_authority="did:rs2:liverion:authority:root",
        targets=["did:rs2:inl:identity:drone-beta-002"],
        scope=RevocationScope(
            jurisdictions=["inl:airspace:restricted-zone-alpha", "inl:airspace:restricted-zone-beta"],
            object_types=["identity_object", "permission_object"],
            constraints={"classification": "restricted", "operator": "INL-OPS"},
        ),
        temporal=TemporalApplicability(
            effective_at="2026-05-10T08:00:00Z",
            issued_at="2026-05-09T17:00:00Z",
        ),
        governance_envelope="env-inl-002",
    )
    print("5. Multi-jurisdiction revocation with constraints:")
    print(r5.to_canonical_json())
    print()

    # --- Expected rejections ---

    print("=== Expected Rejections ===\n")

    # 6. Empty targets list
    try:
        engine.issue(
            rs2_version="0.1",
            revocation_id="rev-bad",
            issuing_authority="did:rs2:auth:1",
            targets=[],
            scope=RevocationScope(jurisdictions=["US-ID"]),
            temporal=TemporalApplicability(effective_at="2026-01-01T00:00:00Z"),
            governance_envelope="env-001",
        )
        print("6. ERROR — should have rejected empty targets")
    except ValueError as e:
        print(f"6. Correctly rejected empty targets: {e}")
    print()

    # 7. Empty jurisdictions in scope
    try:
        RevocationScope(jurisdictions=[])
        print("7. ERROR — should have rejected empty jurisdictions")
    except ValueError as e:
        print(f"7. Correctly rejected empty jurisdictions: {e}")
    print()

    # 8. Malformed effective_at
    try:
        TemporalApplicability(effective_at="not-a-date")
        print("8. ERROR — should have rejected malformed effective_at")
    except (ValueError, TypeError) as e:
        print(f"8. Correctly rejected malformed effective_at: {e}")
    print()

    print("=== All test vectors complete ===")
