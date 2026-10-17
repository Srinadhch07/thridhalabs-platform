"""Pydantic request/response schemas for the authentication API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.admin import Role


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    # Policy (min length) is enforced at account creation, not at login.
    password: str = Field(min_length=1, max_length=256)


class StatusResponse(BaseModel):
    status: str = "ok"


class CsrfResponse(BaseModel):
    csrf_token: str = Field(alias="csrfToken")

    model_config = ConfigDict(populate_by_name=True)


class MeResponse(BaseModel):
    id: str
    email: str
    role: Role
    is_active: bool
