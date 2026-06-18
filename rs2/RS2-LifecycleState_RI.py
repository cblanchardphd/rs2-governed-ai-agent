"""RS2-LifecycleState_RI — Reference Implementation: Lifecycle State

Reduction-to-practice exhibit for patent enablement.
Stdlib only. No external dependencies.

Discipline
- Representation and structural invariants only.
- No transition logic, enforcement, revocation semantics, authority resolution, or trust evaluation.

Serialization
- Emits JSON using schema keys exactly (see Schemas/lifecycle-state.schema.json).
- controller: W3C DID Core §2.3 (formerly governing_authority)
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
class LifecycleState:
    """RS2 Lifecycle State (schema-aligned).

    Required:  rs2_version, lifecycle_state_id, controller
    Optional:  effective_at, supersedes, metadata
    """

    rs2_version: str
    lifecycle_state_id: str
    controller: str          # W3C DID Core §2.3 (formerly governing_authority)

    effective_at: Optional[str] = None
    supersedes: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("rs2_version", "lifecycle_state_id", "controller"):
            val = getattr(self, name)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{name} is required and must be a non-empty string")

        if self.effective_at is not None:
            if not isinstance(self.effective_at, str):
                raise TypeError("effective_at must be a string")
            _parse_rfc3339(self.effective_at)

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
            "lifecycle_state_id": self.lifecycle_state_id,
            "controller": self.controller,
        }
        if self.effective_at is not None:
            d["effective_at"] = self.effective_at
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

class LifecycleStateEngine:
    """Constructs and validates LifecycleState objects."""

    def define(
        self,
        *,
        rs2_version: str,
        lifecycle_state_id: str,
        controller: str,
        effective_at: Optional[str] = None,
        supersedes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LifecycleState:
        """Construct and validate a LifecycleState."""
        return LifecycleState(
            rs2_version=rs2_version,
            lifecycle_state_id=lifecycle_state_id,
            controller=controller,
            effective_at=effective_at,
            supersedes=supersedes,
            metadata=metadata or {},
        )


# ---------------------------------------------------------------------------
# __main__ — test vectors
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = LifecycleStateEngine()

    print("=== RS2-LifecycleState_RI — Test Vectors ===\n")

    # --- Valid cases ---

    # 1. Minimal lifecycle state
    ls1 = engine.define(
        rs2_version="0.1",
        lifecycle_state_id="active",
        controller="did:rs2:liverion:authority:root",
    )
    print("1. Minimal lifecycle state:")
    print(ls1.to_canonical_json())
    print()

    # 2. Lifecycle state with effective_at timestamp
    ls2 = engine.define(
        rs2_version="0.1",
        lifecycle_state_id="active",
        controller="did:rs2:inl:authority:drone-ops",
        effective_at="2026-01-01T00:00:00Z",
        metadata={"label": "Commissioned and operational"},
    )
    print("2. Active state with effective_at (INL drone context):")
    print(ls2.to_canonical_json())
    print()

    # 3. Superseding a prior lifecycle state
    ls3 = engine.define(
        rs2_version="0.1",
        lifecycle_state_id="suspended",
        controller="did:rs2:inl:authority:drone-ops",
        effective_at="2026-03-15T08:00:00Z",
        supersedes=["active"],
        metadata={"reason_code": "maintenance-hold"},
    )
    print("3. Suspended state superseding active:")
    print(ls3.to_canonical_json())
    print()

    # 4. Financial jurisdiction — FINMA regulated asset
    ls4 = engine.define(
        rs2_version="0.1",
        lifecycle_state_id="issued",
        controller="did:rs2:ch:finma-authority",
        effective_at="2026-04-01T09:00:00Z",
        metadata={"instrument": "digital-bond", "jurisdiction": "ch:finma:digital-assets"},
    )
    print("4. Issued state — FINMA regulated asset:")
    print(ls4.to_canonical_json())
    print()

    # 5. Decommissioned state (INL drone retired)
    ls5 = engine.define(
        rs2_version="0.1",
        lifecycle_state_id="decommissioned",
        controller="did:rs2:inl:authority:drone-ops",
        effective_at="2026-05-01T12:00:00Z",
        supersedes=["suspended", "active"],
        metadata={"serial": "DRONE-ALPHA-001"},
    )
    print("5. Decommissioned state (INL drone):")
    print(ls5.to_canonical_json())
    print()

    # 6. Minimal with DID controller — no optional fields
    ls6 = engine.define(
        rs2_version="0.1",
        lifecycle_state_id="initialized",
        controller="did:rs2:eu:eidas2:authority",
    )
    print("6. Initialized state — eIDAS 2.0 authority:")
    print(ls6.to_canonical_json())
    print()

    # --- Expected rejections ---

    print("=== Expected Rejections ===\n")

    # 7. Missing controller
    try:
        engine.define(rs2_version="0.1", lifecycle_state_id="active", controller="")
        print("7. ERROR — should have rejected empty controller")
    except ValueError as e:
        print(f"7. Correctly rejected empty controller: {e}")
    print()

    # 8. Missing lifecycle_state_id
    try:
        engine.define(rs2_version="0.1", lifecycle_state_id="", controller="did:rs2:auth:1")
        print("8. ERROR — should have rejected empty lifecycle_state_id")
    except ValueError as e:
        print(f"8. Correctly rejected empty lifecycle_state_id: {e}")
    print()

    # 9. Malformed effective_at
    try:
        engine.define(
            rs2_version="0.1",
            lifecycle_state_id="active",
            controller="did:rs2:auth:1",
            effective_at="not-a-date",
        )
        print("9. ERROR — should have rejected malformed effective_at")
    except (ValueError, TypeError) as e:
        print(f"9. Correctly rejected malformed effective_at: {e}")
    print()

    print("=== All test vectors complete ===")
