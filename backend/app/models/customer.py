"""Customer — the human (or entity) who owns accounts and grants consent.

Modeled on FDX's customer/contact shape, trimmed to the fields this project
actually uses. Contact details are split into small value objects (name, address)
so the consent layer can reason about them as distinct, minimizable clusters
later (Item 8): a grant for "identity" need not expose "contact", and vice versa.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import field_validator

from .common import CountryCode, EmailStr, EntityId, FdxBaseModel


class PersonName(FdxBaseModel):
    """A person's name, kept structured rather than a single string."""

    first: str
    last: str
    middle: str | None = None

    @property
    def full(self) -> str:
        """Display form: ``First [Middle] Last``."""
        parts = [self.first, self.middle, self.last]
        return " ".join(p for p in parts if p)


class PostalAddress(FdxBaseModel):
    """A mailing address. ``line2`` and ``region`` are optional per locale."""

    line1: str
    city: str
    postal_code: str
    country: CountryCode
    line2: str | None = None
    region: str | None = None  # province / state


class Customer(FdxBaseModel):
    """A customer record: identity plus contact details."""

    customer_id: EntityId
    name: PersonName

    date_of_birth: date | None = None
    emails: list[EmailStr] = []
    #: Phone numbers as provided; normalization to E.164 is out of scope here.
    phones: list[str] = []
    addresses: list[PostalAddress] = []

    @field_validator("date_of_birth")
    @classmethod
    def _dob_not_in_future(cls, value: date | None) -> date | None:
        if value is not None and value > datetime.now(UTC).date():
            raise ValueError("date_of_birth cannot be in the future")
        return value
