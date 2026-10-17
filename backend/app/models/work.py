"""Member work domain model (Work Showcase).

A work is a member-owned, structured-content piece: a title + summary plus an
optional block-based content document. Visibility and publication status are
deliberately independent:
  - publication_status  draft | published | unpublished
  - visibility          private | members | public

Public exposure is composite and enforced server-side: a work is publicly
reachable only when it is PUBLISHED, its visibility is PUBLIC, and the owning
member's profile is PUBLIC (a work is never more visible than its author's
profile policy).

The content document is a strict, versioned JSON schema — never free HTML — so
the API round-trips structured blocks only. Text fields are length-constrained;
mandatory content (external-link URLs, media ids) is enforced here, while
aggregate limits (block count, total text length) are enforced by the service.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.project import ProjectType

MAX_TITLE_LENGTH = 150
MAX_SUMMARY_LENGTH = 2000
MAX_TAG_LENGTH = 100
MAX_TAGS = 50
MAX_BLOCKS = 100
MAX_CAPTION_LENGTH = 300
MAX_TEXT_TOTAL = 100_000
MAX_PARAGRAPH_LENGTH = 10_000
MAX_LINK_LABEL_LENGTH = 200
MAX_URL_LENGTH = 2000
MAX_LIST_ITEMS = 100
MAX_LIST_ITEM_LENGTH = 5000
MAX_GALLERY_IMAGES = 20
MAX_ALT_LENGTH = 300
MAX_QUOTE_LENGTH = 8000
MAX_CODE_LENGTH = 20000


class WorkVisibility(str, Enum):
    PRIVATE = "private"
    MEMBERS = "members"
    PUBLIC = "public"


class WorkPublicationStatus(str, Enum):
    """Publication lifecycle for a work.

    Members move a work through `draft → pending_review → published` (admin
    decides the middle step; a member can never publish through review). The
    legacy direct `publish`/`unpublish` actions remain for backward
    compatibility. `changes_requested` and `rejected` are admin outcomes of a
    review; a `changes_requested`/`rejected`/`unpublished` work can be
    resubmitted.
    """

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"


class ExternalLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(max_length=MAX_LINK_LABEL_LENGTH)
    url: str = Field(max_length=MAX_URL_LENGTH)

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Label must not be empty")
        return value

    @field_validator("url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        from app.core.validators import optional_http_url

        url = optional_http_url(value)
        if url is None:
            raise ValueError("Must be an http(s) URL")
        return url


class InlineRun(BaseModel):
    """An inline text run with optional formatting (rich text support)."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=MAX_PARAGRAPH_LENGTH)
    bold: bool = False
    italic: bool = False
    code: bool = False
    link: str | None = Field(default=None, max_length=MAX_URL_LENGTH)

    @field_validator("text")
    @classmethod
    def _text(cls, value: str) -> str:
        return value.strip()

    @field_validator("link")
    @classmethod
    def _http_link(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.core.validators import optional_http_url

        return optional_http_url(value)


class ParagraphBlock(BaseModel):
    """Paragraph (optionally rich) — spans carry inline formatting."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["paragraph"]
    spans: Annotated[list[InlineRun], Field(max_length=MAX_PARAGRAPH_LENGTH)]


class HeadingBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["heading"]
    level: int = Field(ge=2, le=4)
    text: str = Field(max_length=MAX_PARAGRAPH_LENGTH)


class ImageBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["image"]
    media_id: str = Field(min_length=1, max_length=200)
    caption: str | None = Field(default=None, max_length=MAX_CAPTION_LENGTH)
    alt: str | None = Field(default=None, max_length=MAX_ALT_LENGTH)


class ImageGalleryBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["image_gallery"]
    media_ids: list[str] = Field(max_length=MAX_GALLERY_IMAGES)


class BulletedListBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["bulleted_list"]
    items: list[Annotated[str, Field(max_length=MAX_LIST_ITEM_LENGTH)]] = Field(
        default_factory=list, max_length=MAX_LIST_ITEMS
    )


class NumberedListBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["numbered_list"]
    items: list[Annotated[str, Field(max_length=MAX_LIST_ITEM_LENGTH)]] = Field(
        default_factory=list, max_length=MAX_LIST_ITEMS
    )


class QuoteBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["quote"]
    text: str = Field(max_length=MAX_QUOTE_LENGTH)
    attribution: str | None = Field(default=None, max_length=MAX_QUOTE_LENGTH)


class CodeBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["code"]
    code: str = Field(max_length=MAX_CODE_LENGTH)
    language: str = Field(default="text", max_length=60)


class ExternalLinkBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["external_link"]
    label: str = Field(max_length=MAX_LINK_LABEL_LENGTH)
    url: str = Field(max_length=MAX_URL_LENGTH)

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Label must not be empty")
        return value

    @field_validator("url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        from app.core.validators import optional_http_url

        url = optional_http_url(value)
        if url is None:
            raise ValueError("Must be an http(s) URL")
        return url


class DividerBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["divider"]


ContentBlock = Annotated[
    Union[
        ParagraphBlock,
        HeadingBlock,
        ImageBlock,
        ImageGalleryBlock,
        BulletedListBlock,
        NumberedListBlock,
        QuoteBlock,
        CodeBlock,
        ExternalLinkBlock,
        DividerBlock,
    ],
    Field(discriminator="type"),
]


class ContentDocument(BaseModel):
    """Structured work content — validated block list (never free HTML)."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    blocks: list[ContentBlock] = Field(default_factory=list, max_length=MAX_BLOCKS)

    def media_ids(self) -> list[str]:
        """Every media id referenced anywhere in the document."""
        ids: list[str] = []
        for block in self.blocks:
            if isinstance(block, ImageBlock):
                ids.append(block.media_id)
            elif isinstance(block, ImageGalleryBlock):
                ids.extend(block.media_ids)
        return ids

    @classmethod
    def template_blocks(cls, template: str) -> list[ContentBlock]:
        """Seed the supported work templates with ordinary, editable blocks
        (templates are just starting points — never a locked format)."""
        blank = ParagraphBlock(type="paragraph", spans=[InlineRun(text="")])
        if template == "project-showcase":
            return [
                HeadingBlock(type="heading", level=2, text="Overview"),
                blank,
                HeadingBlock(type="heading", level=2, text="Highlights"),
                BulletedListBlock(type="bulleted_list", items=[""]),
                DividerBlock(type="divider"),
                HeadingBlock(type="heading", level=2, text="Results"),
                ParagraphBlock(type="paragraph", spans=[InlineRun(text="")]),
            ]
        if template == "research":
            return [
                HeadingBlock(type="heading", level=2, text="Question"),
                ParagraphBlock(type="paragraph", spans=[InlineRun(text="")]),
                HeadingBlock(type="heading", level=2, text="Approach"),
                ParagraphBlock(type="paragraph", spans=[InlineRun(text="")]),
                NumberedListBlock(type="numbered_list", items=[""]),
                HeadingBlock(type="heading", level=2, text="Findings"),
                QuoteBlock(type="quote", text="", attribution=""),
            ]
        if template == "creative-portfolio":
            return [
                HeadingBlock(type="heading", level=2, text="Concept"),
                ParagraphBlock(type="paragraph", spans=[InlineRun(text="")]),
                DividerBlock(type="divider"),
                HeadingBlock(type="heading", level=2, text="Gallery"),
                ImageGalleryBlock(type="image_gallery", media_ids=[]),
                DividerBlock(type="divider"),
                HeadingBlock(type="heading", level=2, text="Process"),
                ParagraphBlock(type="paragraph", spans=[InlineRun(text="")]),
            ]
        return [blank]


class MemberWork(BaseModel):
    """Internal member-work representation. Never serialised directly.

    `version` increments on every update; certification snapshots freeze the
    version they were captured at so "changed since review" can be derived
    without trusting timestamps alone.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    member_id: str
    title: str
    slug: str
    summary: str
    cover_media_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    external_links: list[ExternalLink] = Field(max_length=20)
    content: ContentDocument = Field(default_factory=ContentDocument)
    visibility: WorkVisibility = WorkVisibility.PRIVATE
    publication_status: WorkPublicationStatus = WorkPublicationStatus.DRAFT
    version: int = 0
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None

    # Publication review (member submission → admin decision). Independent of
    # certification review; a work may be submitted for publication review
    # before it is published, and once published can still be certified.
    submitted_at: datetime | None = None
    review_feedback: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None

    # Official Projects featuring. Only admins can change this; a featured work
    # is surfaced on the official Projects page (subject to the same composite
    # public-visibility rules as any other work).
    featured_on_projects: bool = False
    featured_classification: ProjectType | None = None
    featured_at: datetime | None = None
    featured_by: str | None = None