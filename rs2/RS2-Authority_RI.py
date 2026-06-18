"""RS2-Authority_RI — Risk-Surface Reduction Substrate: Authority Object
Reference Implementation (Reduction-to-Practice Exhibit)

Stdlib only. No external dependencies.

Demonstrates:
  - AuthorityScope and AuthorityObject construction with full invariant enforcement
  - Forbidden metadata key detection (trust / enforcement / identity embedding)
  - Schema-shaped JSON serialization
  - AuthorityEngine as the single construction entry point
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional


# ---------------------------------------------------------------------------
# Invariant constants
# ---------------------------------------------------------------------------

_FORBIDDEN_METADATA_KEY_FRAGMENTS: FrozenSet[str] = frozenset({
    "trust", "trusted", "trust_anchor", "root",
    "priority", "rank", "legitimacy", "accredit", "certif",
    "authorize", "authorization", "permission", "permit", "deny",
    "policy", "enforce", "enforcement", "decision", "runtime",
    "identity_object", "identity_id_object",
})


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AuthorityScope:
    """Declarative boundary within which an authority may operate.

    Shared canonical primitive — used by all seven RS2 identity columns.
    Do not flatten into column-specific dataclasses.
    """

    jurisdictions: List[str]
    object_types: Optional[List[str]] = None
    constraints: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.jurisdictions, list) or not self.jurisdictions:
            raise ValueError("scope.jurisdictions must be a non-empty list")
        for j in self.jurisdictions:
            if not isinstance(j, str) or not j.strip():
                raise ValueError("each scope.jurisdictions entry must be a non-empty string")
        if self.object_types is not None:
            if not isinstance(self.object_types, list):
                raise ValueError("scope.object_types must be a list when provided")
            for t in self.object_types:
                if not isinstance(t, str) or not t.strip():
                    raise ValueError("each scope.object_types entry must be a non-empty string")
        if self.constraints is None:
            object.__setattr__(self, "constraints", {})
        if not isinstance(self.constraints, dict):
            raise ValueError("scope.constraints must be a dict when provided")

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"jurisdictions": list(self.jurisdictions)}
        if self.object_types is not None:
            d["object_types"] = list(self.object_types)
        if self.constraints:
            d["constraints"] = dict(self.constraints)
        return d


@dataclass(frozen=True, slots=True)
class AuthorityObject:
    """Immutable RS2 Authority Object — declares governance capacity, nothing more.

    principal_ref identifies the identity_id of the governed object (Entity, Individual,
    or Machine) that holds this authority. It is optional in this RI to preserve
    declarative purity — an authority declaration is valid without a principal binding.
    In production deployments, principal_ref MUST be populated to enable:
      - delegation chain traversal (who delegated to whom)
      - supervisory controls (who oversees this authority holder)
      - EU AI Act Article 14 human oversight compliance (who is the accountable principal)

    principal_ref MUST reference an identity_id from the RS2 Identity Object of the
    holding Entity or Individual. It MUST NOT embed identity data directly.
    """

    rs2_version: str
    authority_id: str
    authority_type: str
    scope: AuthorityScope
    principal_ref: Optional[str] = None   # identity_id of the authority holder — required in production
    supersedes: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "rs2_version": self.rs2_version,
            "authority_id": self.authority_id,
            "authority_type": self.authority_type,
            "scope": self.scope.to_dict(),
        }
        if self.principal_ref is not None:
            d["principal_ref"] = self.principal_ref
        if self.supersedes is not None:
            d["supersedes"] = list(self.supersedes)
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class AuthorityEngine:
    """Constructs validated RS2 Authority Objects.

    Enforces all structural invariants:
    - Authority is distinct from identity, trust, and enforcement.
    - No forbidden semantics in metadata keys.
    - Required fields non-empty; scope has at least one jurisdiction.
    - Immutable once constructed.
    """

    def construct(
        self,
        *,
        rs2_version: str,
        authority_id: str,
        authority_type: str,
        jurisdictions: List[str],
        object_types: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        principal_ref: Optional[str] = None,
        supersedes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuthorityObject:
        for name, val in (
            ("rs2_version", rs2_version),
            ("authority_id", authority_id),
            ("authority_type", authority_type),
        ):
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{name} must be a non-empty string")

        scope = AuthorityScope(
            jurisdictions=jurisdictions,
            object_types=object_types,
            constraints=constraints or {},
        )

        if principal_ref is not None:
            if not isinstance(principal_ref, str) or not principal_ref.strip():
                raise ValueError("principal_ref must be a non-empty string when provided")

        if supersedes is not None:
            if not isinstance(supersedes, list):
                raise ValueError("supersedes must be a list when provided")
            for s in supersedes:
                if not isinstance(s, str) or not s.strip():
                    raise ValueError("each supersedes entry must be a non-empty string")

        meta = metadata or {}
        self._check_metadata_invariants(meta)

        return AuthorityObject(
            rs2_version=rs2_version,
            authority_id=authority_id,
            authority_type=authority_type,
            scope=scope,
            principal_ref=principal_ref,
            supersedes=supersedes,
            metadata=meta,
        )

    @staticmethod
    def _check_metadata_invariants(metadata: Dict[str, Any]) -> None:
        """Reject metadata keys that encode trust, enforcement, or identity semantics."""
        for k in metadata:
            lk = str(k).lower()
            for frag in _FORBIDDEN_METADATA_KEY_FRAGMENTS:
                if frag in lk:
                    raise ValueError(
                        f"metadata key '{k}' encodes out-of-scope semantics (matched '{frag}')"
                    )


# ---------------------------------------------------------------------------
# __main__ — test vectors
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = AuthorityEngine()

    vectors = [
        # 1. Minimal institutional authority
        dict(
            rs2_version="1.0",
            authority_id="auth-liverion-001",
            authority_type="institutional authority",
            jurisdictions=["CH"],
        ),
        # 2. Regulatory authority, multiple jurisdictions
        dict(
            rs2_version="1.0",
            authority_id="auth-finma-001",
            authority_type="regulatory authority",
            jurisdictions=["CH", "LI"],
            metadata={"label": "FINMA Swiss Financial Supervisory Authority"},
        ),
        # 3. Delegated authority with object-type scope
        dict(
            rs2_version="1.0",
            authority_id="auth-delegate-sdx-001",
            authority_type="delegated authority",
            jurisdictions=["CH"],
            object_types=["attestation", "identity-object"],
            metadata={"label": "SIX Digital Exchange delegated issuer"},
        ),
        # 4. Superseding authority
        dict(
            rs2_version="1.0",
            authority_id="auth-inl-v2-001",
            authority_type="organizational authority",
            jurisdictions=["US-ID"],
            supersedes=["auth-inl-v1-001"],
            metadata={"label": "INL RS2 Authority v2"},
        ),
        # 5. Scoped constraints
        dict(
            rs2_version="1.0",
            authority_id="auth-drone-oem-001",
            authority_type="oem authority",
            jurisdictions=["US"],
            object_types=["attestation"],
            constraints={"domain": "autonomous-systems", "platform": "drone"},
        ),
        # 6. Multi-jurisdiction regulatory
        dict(
            rs2_version="1.0",
            authority_id="auth-eidas-notified-001",
            authority_type="regulatory authority",
            jurisdictions=["DE", "FR", "NL", "BE"],
            object_types=["identity-object", "attestation", "permission-object"],
            metadata={"label": "eIDAS notified body — multi-jurisdiction"},
        ),
        # 7. Invariant rejection — forbidden metadata key
        dict(
            rs2_version="1.0",
            authority_id="auth-bad-001",
            authority_type="institutional authority",
            jurisdictions=["US"],
            metadata={"trust_anchor": "root-ca"},
        ),
        # 8. Invariant rejection — empty jurisdiction
        dict(
            rs2_version="1.0",
            authority_id="auth-bad-002",
            authority_type="institutional authority",
            jurisdictions=[],
        ),
    ]

    for i, v in enumerate(vectors, 1):
        label = v.get("metadata", {}).get("label") or v.get("authority_id", "")
        try:
            obj = engine.construct(**v)
            print(f"[{i}] OK  {obj.authority_id}  {obj.scope.jurisdictions}")
            print(f"     {obj.to_json()}\n")
        except ValueError as exc:
            print(f"[{i}] ERR (expected) — {exc}\n")
