"""Shared model primitives: ObjectId handling, serialization, validators."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated, Any, Generic, TypeVar

from bson import ObjectId
from pydantic import AfterValidator, BaseModel, ConfigDict
from pydantic_core import core_schema


class _ObjectIdType:
    """Pydantic v2 core-schema adapter so models can hold real ``ObjectId``s."""

    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler):
        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

    @staticmethod
    def validate(value: Any) -> ObjectId:
        if isinstance(value, ObjectId):
            return value
        if isinstance(value, str) and ObjectId.is_valid(value):
            return ObjectId(value)
        raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[ObjectId, _ObjectIdType]


def stringify_ids(value: Any) -> Any:
    """Recursively convert ObjectId values to strings for API output."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [stringify_ids(v) for v in value]
    if isinstance(value, dict):
        return {k: stringify_ids(v) for k, v in value.items()}
    return value


def utcnow() -> datetime:
    # Naive UTC: MongoDB stores/returns naive-UTC datetimes, so we keep storage and
    # comparisons consistently naive to avoid offset-naive vs offset-aware errors.
    return datetime.now(timezone.utc).replace(tzinfo=None)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    cleaned = value.strip().lower()
    if not _EMAIL_RE.match(cleaned):
        raise ValueError("Invalid email address")
    return cleaned


Email = Annotated[str, AfterValidator(_validate_email)]


class OutBase(BaseModel):
    """Base for API response models. ``from_doc`` stringifies ObjectIds and maps
    Mongo's ``_id`` to ``id`` so responses use clean ``id`` keys (FastAPI
    serializes response models by alias, so we rename rather than alias)."""

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_doc(cls, doc: dict) -> "OutBase":
        data = stringify_ids(dict(doc))
        if "_id" in data:
            data["id"] = data.pop("_id")
        return cls.model_validate(data)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
