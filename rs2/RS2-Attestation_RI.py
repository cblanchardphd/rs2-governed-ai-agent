"""RS2-Attestation_RI — Risk-Surface Reduction Substrate: Attestation
Reference Implementation (Reduction-to-Practice Exhibit)

Stdlib only. No external dependencies.

Demonstrates:
  - TemporalApplicability and Attestation construction with full invariant enforcement
  - additionalProperties=false at top-level and temporal sub-object
  - RFC 3339 date-time string validation (best-effort)
  - AttestationEngine as the single construction entry point

Non-goals (per RS2 spec):
  - No verification/validation procedures
  - No trust or reliance determination
  - No evidence evaluation
  - No compliance/certification logic
  - No enforcement behavior
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
    "rs2_version", "attestation_id", "subject_identity",
    "issuing_authority", "assertion", "governance_envelope", "temporal",
})
_ALLOWED_KEYS = _REQUIRED_KEYS | frozenset({"supersedes", "metadata"})
_TEMPORAL_REQUIRED = frozenset({"asserted_at"})
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
    """Temporal window sub-object for an RS2 Attestation (representation only)."""

    asserted_at: str
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"asserted_at": self.asserted_at}
        if self.valid_from is not None:
            d["valid_from"] = self.valid_from
        if self.valid_until is not None:
            d["valid_until"] = self.valid_until
        return d


@dataclass(frozen=True, slots=True)
class Attestation:
    """Immutable RS2 Attestation — assertion about a subject identity, nothing more."""

    rs2_version: str
    attestation_id: str
    subject_identity: str
    issuing_authority: str
    assertion: str
    governance_envelope: str
    temporal: TemporalApplicability
    supersedes: Optional[Sequence[str]] = None
    metadata: Optional[Mapping[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "rs2_version": self.rs2_version,
            "attestation_id": self.attestation_id,
            "subject_identity": self.subject_identity,
            "issuing_authority": self.issuing_authority,
            "assertion": self.assertion,
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

class AttestationEngine:
    """Constructs validated RS2 Attestation objects.

    Enforces all structural invariants:
    - Required fields non-empty strings.
    - additionalProperties=false at top-level and temporal.
    - temporal.asserted_at is a valid RFC 3339 date-time string.
    - supersedes entries are non-empty strings when provided.
    - Immutable once constructed.
    """

    def issue(
        self,
        *,
        rs2_version: str,
        attestation_id: str,
        subject_identity: str,
        issuing_authority: str,
        assertion: str,
        governance_envelope: str,
        asserted_at: str,
        valid_from: Optional[str] = None,
        valid_until: Optional[str] = None,
        supersedes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Attestation:
        for name, val in (
            ("rs2_version", rs2_version),
            ("attestation_id", attestation_id),
            ("subject_identity", subject_identity),
            ("issuing_authority", issuing_authority),
            ("assertion", assertion),
            ("governance_envelope", governance_envelope),
            ("asserted_at", asserted_at),
        ):
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{name} must be a non-empty string")

        _parse_rfc3339(asserted_at)
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
            asserted_at=asserted_at,
            valid_from=valid_from,
            valid_until=valid_until,
        )

        return Attestation(
            rs2_version=rs2_version,
            attestation_id=attestation_id,
            subject_identity=subject_identity,
            issuing_authority=issuing_authority,
            assertion=assertion,
            governance_envelope=governance_envelope,
            temporal=temporal,
            supersedes=supersedes,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# __main__ — test vectors
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = AttestationEngine()

    vectors = [
        # 1. Minimal attestation — drone identity
        dict(
            rs2_version="1.0",
            attestation_id="att-drone-inl-001",
            subject_identity="id-drone-inl-alpha-001",
            issuing_authority="auth-inl-v2-001",
            assertion="subject identity has passed pre-flight operational check",
            governance_envelope="ge-inl-drone-ops-001",
            asserted_at="2026-05-12T10:00:00Z",
        ),
        # 2. Attestation with validity window
        dict(
            rs2_version="1.0",
            attestation_id="att-satellite-swissre-001",
            subject_identity="id-sat-leo-orbit-001",
            issuing_authority="auth-oem-orbital-001",
            assertion="satellite bus conforms to RS2 identity binding at launch",
            governance_envelope="ge-swissre-space-001",
            asserted_at="2026-05-12T08:00:00Z",
            valid_from="2026-05-12T08:00:00Z",
            valid_until="2027-05-12T08:00:00Z",
        ),
        # 3. Attestation with supersedes
        dict(
            rs2_version="1.0",
            attestation_id="att-rivian-ecu-v2-001",
            subject_identity="id-rivian-ecu-001",
            issuing_authority="auth-rivian-oem-001",
            assertion="ECU firmware version 2.1.0 is installed and conforms to OEM specification",
            governance_envelope="ge-rivian-fleet-001",
            asserted_at="2026-05-12T12:00:00Z",
            supersedes=["att-rivian-ecu-v1-001"],
        ),
        # 4. eIDAS machine identity attestation
        dict(
            rs2_version="1.0",
            attestation_id="att-eidas-iot-001",
            subject_identity="id-iot-device-eu-001",
            issuing_authority="auth-eidas-notified-001",
            assertion="device identity conforms to EUDI wallet binding requirements",
            governance_envelope="ge-eidas-iot-001",
            asserted_at="2026-05-12T09:30:00Z",
            valid_from="2026-05-12T09:30:00Z",
            valid_until="2027-05-12T09:30:00Z",
            metadata={"standard": "EUDI-ARF-1.4", "jurisdiction": "EU"},
        ),
        # 5. Attestation with metadata
        dict(
            rs2_version="1.0",
            attestation_id="att-sdx-participant-001",
            subject_identity="id-bank-six-participant-001",
            issuing_authority="auth-finma-001",
            assertion="institution is licensed for digital asset settlement under SDX framework",
            governance_envelope="ge-sdx-settlement-001",
            asserted_at="2026-05-12T00:00:00Z",
            metadata={"license_number": "FINMA-2026-0042", "tier": "full-participant"},
        ),
        # 6. Invariant rejection — empty assertion
        dict(
            rs2_version="1.0",
            attestation_id="att-bad-001",
            subject_identity="id-x-001",
            issuing_authority="auth-x-001",
            assertion="",
            governance_envelope="ge-x-001",
            asserted_at="2026-05-12T00:00:00Z",
        ),
        # 7. Invariant rejection — malformed date-time
        dict(
            rs2_version="1.0",
            attestation_id="att-bad-002",
            subject_identity="id-x-001",
            issuing_authority="auth-x-001",
            assertion="some assertion",
            governance_envelope="ge-x-001",
            asserted_at="not-a-date",
        ),
    ]

    for i, v in enumerate(vectors, 1):
        try:
            obj = engine.issue(**v)
            print(f"[{i}] OK  {obj.attestation_id}")
            print(f"     {obj.to_json()}\n")
        except (ValueError, TypeError) as exc:
            print(f"[{i}] ERR (expected) — {exc}\n")
