"""Careers domain models: public page settings singleton + opportunity records.

Careers is intentionally small — a public opportunity board that applies by
email. There is no applicant account, application form or tracking system.
Visibility rules are enforced server-side: only `open` opportunities are ever
visible through public APIs, and nothing is exposed while careers are disabled.

Lab participation terminology: an opportunity is a participation role in the
lab (e.g. "Lab Member"), never an employment/internship claim about people.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.validators import optional_email

SINGLETON_KEY = "careers"


class OpportunityType(str, Enum):
    LAB_MEMBER = "lab-member"
    INTERNSHIP = "internship"
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    OTHER = "other"


class WorkMode(str, Enum):
    REMOTE = "remote"
    ON_SITE = "on-site"
    HYBRID = "hybrid"
    FLEXIBLE = "flexible"


class OpportunityStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class CareersSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    singleton: str = SINGLETON_KEY
    enabled: bool = False
    heading: str = ""
    description: str = ""
    application_email: str | None = None
    application_template: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("application_email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return optional_email(value)


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    slug: str
    type: OpportunityType
    custom_type: str | None = None
    description: str = ""
    skills: list[str] = []
    work_mode: WorkMode | None = None
    application_email: str | None = None
    status: OpportunityStatus = OpportunityStatus.DRAFT
    display_order: int = 0
    created_at: datetime
    updated_at: datetime


def default_careers_settings_doc() -> dict:
    """The empty Careers settings state — new installs start disabled."""
    return {
        "singleton": SINGLETON_KEY,
        "enabled": False,
        "heading": "",
        "description": "",
        "application_email": None,
        "application_template": None,
    }