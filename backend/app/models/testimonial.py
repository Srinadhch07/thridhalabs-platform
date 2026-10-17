"""Testimonial domain model.

Testimonials can arrive two ways: admins manage them directly, and public
visitors may submit them for review. `status` is the moderation state owned
exclusively by the server/admins — `published` gates public visibility and
`featured` promotes an item to homepage-level listings.
"""

from __future__ import annotations

from datetime import datetime
from datetime import date as DateValue
from enum import Enum

from pydantic import BaseModel, ConfigDict


class TestimonialStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Testimonial(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    client_id: str | None = None
    person_name: str
    role: str = ""
    testimonial_text: str
    profile_image_media_id: str | None = None
    company: str | None = None
    rating: int = 5
    featured: bool = False
    published: bool = False
    status: TestimonialStatus = TestimonialStatus.PENDING
    display_order: int = 0
    date: DateValue | None = None
    created_at: datetime
    updated_at: datetime