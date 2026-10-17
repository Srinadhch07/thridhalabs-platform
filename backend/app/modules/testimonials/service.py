"""Testimonials service: CRUD, media/client reference validation, publishing
rules (published-only public exposure)."""

from __future__ import annotations

from app.core.bson import serialize_for_mongo
from app.core.errors import AppError
from app.models.client import Client
from app.models.testimonial import Testimonial, TestimonialStatus
from app.modules.clients import repository as clients_repository
from app.modules.testimonials import repository
from app.modules.testimonials.schemas import (
    ClientPublicRef,
    ClientRef,
    TestimonialCreate,
    TestimonialSubmit,
    TestimonialUpdate,
)
from app.services.references import require_client_exists, require_media_exist


def _resolve_status(
    explicit: TestimonialStatus | None, published: bool | None
) -> TestimonialStatus:
    """Moderation state for a write. An explicit status always wins;
    otherwise an item marked published is treated as approved (preserves the
    pre-moderation admin behavior), everything else starts pending."""
    if explicit is not None:
        return explicit
    if published:
        return TestimonialStatus.APPROVED
    return TestimonialStatus.PENDING


async def create_testimonial(payload: TestimonialCreate) -> Testimonial:
    data = serialize_for_mongo(payload.model_dump(exclude_unset=True))
    await require_client_exists(data.get("client_id"))
    await require_media_exist([data.get("profile_image_media_id")])
    status = _resolve_status(data.get("status"), data.get("published"))
    data["status"] = status
    # `published` is the visibility gate: only approved items may be public.
    data["published"] = status == TestimonialStatus.APPROVED
    insert_data = {
        key: value for key, value in data.items()
        if key not in ("person_name", "testimonial_text")
    }
    return await repository.insert(
        person_name=data["person_name"],
        testimonial_text=data["testimonial_text"],
        **insert_data,
    )


async def submit_testimonial(payload: TestimonialSubmit) -> None:
    """Store a public submission as pending. Moderation fields can never come
    from the client — the submit schema drops them and the server forces the
    pending/unpublished/unfeatured state."""
    data = serialize_for_mongo(payload.model_dump(exclude_unset=True))
    await repository.insert(
        person_name=data["person_name"],
        testimonial_text=data["testimonial_text"],
        role=data.get("role", ""),
        company=data.get("company"),
        rating=data.get("rating", 5),
        featured=False,
        published=False,
        status=TestimonialStatus.PENDING,
        display_order=0,
    )


async def get_testimonial(testimonial_id: str) -> Testimonial:
    item = await repository.find_by_id(testimonial_id)
    if item is None:
        raise AppError(404, "TESTIMONIAL_NOT_FOUND", "Testimonial was not found")
    return item


async def update_testimonial(testimonial_id: str, payload: TestimonialUpdate) -> Testimonial:
    existing = await get_testimonial(testimonial_id)
    data = serialize_for_mongo(payload.model_dump(exclude_unset=True))

    if "client_id" in data:
        await require_client_exists(data.get("client_id"))
    if "profile_image_media_id" in data:
        await require_media_exist([data.get("profile_image_media_id")])

    fields = {key: value for key, value in data.items() if value is not None}
    for key in ("client_id", "profile_image_media_id", "company", "role",
                "person_name", "testimonial_text"):
        if key in data and data[key] is None:
            fields[key] = None
    if "status" in fields:
        # An explicit moderation decision re-derives visibility.
        fields["published"] = fields["status"] == TestimonialStatus.APPROVED

    updated = await repository.update(testimonial_id, fields)
    if updated is None:
        raise AppError(404, "TESTIMONIAL_NOT_FOUND", "Testimonial was not found")
    return updated


async def delete_testimonial(testimonial_id: str) -> None:
    await get_testimonial(testimonial_id)
    await repository.delete_by_id(testimonial_id)


async def list_testimonials(
    *, page: int, page_size: int, query: dict, sort: list[tuple]
) -> tuple[list[Testimonial], int]:
    return await repository.list_testimonials(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )


async def admin_client_ref(client_id: str | None) -> ClientRef | None:
    if not client_id:
        return None
    client = await clients_repository.find_by_id(client_id)
    if client is None:
        return None
    return ClientRef(id=client.id, slug=client.slug, name=client.name)


async def _public_client_ref(client_id: str | None) -> ClientPublicRef | None:
    if not client_id:
        return None
    client = await clients_repository.find_by_id(client_id)
    if client is None:
        return None
    return ClientPublicRef(slug=client.slug, name=client.name)


def _public_client_map_count(items: list[Testimonial], clients: dict[str, Client]) -> dict[str, ClientPublicRef]:
    return {
        item.id: (
            ClientPublicRef(slug=clients[item.client_id].slug, name=clients[item.client_id].name)
            if item.client_id and item.client_id in clients else None
        )
        for item in items
    }


async def list_public(   # noqa: PLR0913  (mirrors callers' filter shape)
    *,
    page: int, page_size: int, published: bool = True,
    featured: bool | None = None, client_id: str | None = None,
    sort: list[tuple],
) -> tuple[list[Testimonial], dict[str, ClientPublicRef], int]:
    # Public visibility needs BOTH gates: approved moderation status and the
    # published flag. The `$exists` branch keeps pre-moderation documents
    # (no `status` field) behaving exactly as before — published ones stay
    # visible — while every new write always carries an explicit status.
    query: dict = {
        "published": published,
        "$or": [
            {"status": TestimonialStatus.APPROVED.value},
            {"status": {"$exists": False}},
        ],
    }
    if featured is not None:
        query["featured"] = featured
    if client_id:
        query["client_id"] = client_id
    # Default listing floats featured testimonials to the top.
    if sort and sort[0][0] == "display_order":
        sort = [("featured", -1), *sort]
    items, total = await repository.list_testimonials(
        query=query, sort=sort, skip=(page - 1) * page_size, limit=page_size
    )
    ids = {item.client_id for item in items if item.client_id}
    clients = await clients_repository.find_many_by_ids(list(ids))
    refs = _public_client_map_count(items, clients)
    return items, refs, total


async def get_public(testimonial_id: str) -> tuple[Testimonial, ClientPublicRef | None]:
    item = await repository.find_by_id(testimonial_id)
    if (
        item is None
        or item.status != TestimonialStatus.APPROVED
        or not item.published
    ):
        raise AppError(404, "TESTIMONIAL_NOT_FOUND", "Testimonial was not found")
    ref = await _public_client_ref(item.client_id)
    return item, ref