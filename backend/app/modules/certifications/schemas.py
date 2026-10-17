"""Pydantic schemas for the certification-review API (member + admin surfaces).

The reviewer judges the frozen `snapshot`, never the live work; the live work's
current version is only used to flag `changed_since_review`. Raw Mongo ids and
internal fields never cross the boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.certificate import CertificateRef
from app.models.certification import (
    CertificationDecision,
    CertificationRequest,
    CertificationSnapshot,
    CertificationStatus,
    TERMINAL_STATUSES,
)

MAX_FEEDBACK_LENGTH = 4000

ReviewAction = Literal["under_review", "approve", "request_changes", "reject"]


class CertificationApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_id: str = Field(min_length=1, max_length=64)


class CertificationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReviewAction
    feedback: str | None = Field(default=None, max_length=MAX_FEEDBACK_LENGTH)

    def clean_feedback(self) -> str | None:
        if self.feedback is None:
            return None
        value = self.feedback.strip()
        return value or None


class CertificationWorkRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    slug: str


class CertificationMemberRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    name: str


def _changed_since_review(request: CertificationRequest, current_version: int) -> bool:
    if request.status not in TERMINAL_STATUSES:
        return False
    return current_version > request.version_reviewed


class CertificationCardResponse(BaseModel):
    """List item — excludes the heavy snapshot."""

    model_config = ConfigDict(extra="forbid")

    id: str
    status: CertificationStatus
    active: bool
    work: CertificationWorkRef
    member: CertificationMemberRef
    snapshot_version: int
    version_reviewed: int
    changed_since_review: bool
    submitted_at: datetime
    decided_at: datetime | None

    @classmethod
    def from_request(
        cls,
        request: CertificationRequest,
        *,
        work_title: str,
        work_slug: str,
        current_version: int,
        member_name: str,
    ) -> "CertificationCardResponse":
        return cls(
            id=request.id,
            status=request.status,
            active=request.active,
            work=CertificationWorkRef(id=request.work_id, title=work_title, slug=work_slug),
            member=CertificationMemberRef(member_id=request.member_id, name=member_name),
            snapshot_version=request.snapshot_version,
            version_reviewed=request.version_reviewed,
            changed_since_review=_changed_since_review(request, current_version),
            submitted_at=request.submitted_at,
            decided_at=request.decided_at,
        )


class CertificationDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: CertificationStatus
    active: bool
    work: CertificationWorkRef
    member: CertificationMemberRef
    snapshot: CertificationSnapshot
    snapshot_version: int
    version_reviewed: int
    changed_since_review: bool
    captured_at: datetime
    submitted_at: datetime
    decided_at: datetime | None
    decided_by: str | None
    decided_by_role: str | None
    latest_feedback: str | None
    decisions: list[CertificationDecision]
    created_at: datetime
    updated_at: datetime
    certificate: CertificateRef | None = None

    @classmethod
    def from_request(
        cls,
        request: CertificationRequest,
        *,
        work_title: str,
        work_slug: str,
        current_version: int,
        member_name: str,
    ) -> "CertificationDetailResponse":
        return cls(
            id=request.id,
            status=request.status,
            active=request.active,
            work=CertificationWorkRef(id=request.work_id, title=work_title, slug=work_slug),
            member=CertificationMemberRef(member_id=request.member_id, name=member_name),
            snapshot=request.snapshot,
            snapshot_version=request.snapshot_version,
            version_reviewed=request.version_reviewed,
            changed_since_review=_changed_since_review(request, current_version),
            captured_at=request.captured_at,
            submitted_at=request.submitted_at,
            decided_at=request.decided_at,
            decided_by=request.decided_by,
            decided_by_role=request.decided_by_role,
            latest_feedback=request.latest_feedback,
            decisions=request.decisions,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )


class CertificationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CertificationCardResponse]
    total: int
    page: int
    page_size: int
    pages: int