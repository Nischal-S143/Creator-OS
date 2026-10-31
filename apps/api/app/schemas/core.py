import uuid
from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from fastapi import Query
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints, field_validator

T = TypeVar("T")

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", min_length=2, max_length=100)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Role = Literal["owner", "admin", "manager", "editor", "analyst", "client_approver"]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


class Request(BaseModel):
    # Unknown fields are refused, so a client cannot smuggle in organization_id or meko_datapack_id.
    model_config = ConfigDict(extra="forbid")


class Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class OrganizationCreate(Request):
    name: Name
    slug: Slug


class OrganizationOut(Response):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    status: str
    created_at: datetime


class OrganizationWithRole(OrganizationOut):
    role: Role


class UserOut(Response):
    id: uuid.UUID
    email: str


class MeOut(UserOut):
    organizations: list[OrganizationWithRole]


class MemberAdd(Request):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]
    role: Role

    @field_validator("email")
    @classmethod
    def looks_like_email(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("must be an email address")
        return value.lower()


class MemberUpdate(Request):
    role: Role | None = None
    status: Literal["active", "removed"] | None = None


class MemberOut(Response):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    role: Role
    status: str


class BrandCreate(Request):
    name: Name
    slug: Slug
    industry: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    website_url: AnyHttpUrl | None = None


class BrandUpdate(Request):
    name: Name | None = None
    industry: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    website_url: AnyHttpUrl | None = None
    owner_id: uuid.UUID | None = Field(default=None)


class BrandOut(Response):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    industry: str | None
    website_url: str | None
    owner_id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
