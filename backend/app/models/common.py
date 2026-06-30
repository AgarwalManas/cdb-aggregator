"""Shared building blocks for the canonical, FDX-aligned domain model.

Everything here is deliberately small and reused across the entity modules so the
canonical types stay consistent: one money representation, one currency rule, one
base-model configuration. Keeping these in one place is what lets every source
(Items 3-5) normalize into the *same* shapes the consent layer (Items 7-8) gates.

Design choices worth calling out:

* **Money is ``Decimal``, never ``float``.** Binary floats can't represent values
  like ``0.10`` exactly; for financial data that is a correctness bug, not a
  rounding nicety. All amounts use a fixed-precision ``Decimal``.
* **camelCase on the wire.** FDX (and most JSON APIs) use camelCase. Fields are
  pythonic ``snake_case`` in code but serialize to camelCase via an alias
  generator, so ``model_dump(by_alias=True)`` reads as FDX-shaped JSON while the
  code stays idiomatic. Input accepts either form.
* **Timestamps are timezone-aware.** Naive datetimes are rejected — an audit log
  (Item 8) that can't pin an event to an absolute instant isn't worth much.
* **``extra="forbid"``.** The canonical model is the contract; an unexpected field
  is almost always a normalizer bug, so we surface it loudly instead of silently
  dropping it.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

# --- Reusable, self-validating field types ----------------------------------

#: ISO 4217 alphabetic currency code, e.g. ``CAD``, ``USD``. Format-validated
#: (three uppercase letters); we intentionally don't ship the full code table.
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]

#: ISO 3166-1 alpha-2 country code, e.g. ``CA``, ``US``.
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]

#: A non-empty identifier. Whitespace is stripped (see base config) before the
#: length check, so ``"  "`` is rejected as empty.
EntityId = Annotated[str, StringConstraints(min_length=1)]

#: A monetary amount. Signed is allowed at this level (balances can be negative,
#: e.g. an overdraft or a loan liability); entities that must be non-negative
#: (a holding quantity, a transaction amount) add their own ``ge=`` constraint.
Money = Annotated[Decimal, Field(max_digits=20, decimal_places=4)]

#: A lightweight email check that avoids pulling in an extra dependency. Not
#: RFC-5322 exhaustive — just enough to catch obviously malformed input.
EmailStr = Annotated[str, StringConstraints(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class FdxBaseModel(BaseModel):
    """Base class for every canonical type.

    Centralizes the serialization and validation policy described in this
    module's docstring so individual entities only declare their fields.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # accept snake_case field names too
        extra="forbid",
        str_strip_whitespace=True,
    )
