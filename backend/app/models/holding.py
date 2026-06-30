"""InvestmentHolding — one position within an investment account.

Modeled on FDX's investment holding. Market value can be supplied directly or
derived from ``quantity × current_unit_price`` when the source gives the pieces
but not the product — a small convenience the normalizer (Item 5) leans on.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, Field, model_validator

from .common import CurrencyCode, EntityId, FdxBaseModel, Money


class HoldingType(StrEnum):
    """Security class of the position — a pragmatic subset of FDX values."""

    EQUITY = "EQUITY"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    FIXED_INCOME = "FIXED_INCOME"
    OPTION = "OPTION"
    CASH = "CASH"
    CRYPTO = "CRYPTO"
    OTHER = "OTHER"


class InvestmentHolding(FdxBaseModel):
    """A single holding (position) in an investment account."""

    holding_id: EntityId
    account_id: EntityId
    holding_type: HoldingType

    #: Ticker symbol if applicable (e.g. ``"VFV"``). Optional — not every
    #: holding (cash, some fixed income) has one.
    symbol: str | None = None
    #: Security identifier (CUSIP/ISIN/etc.) if the source provides it.
    security_id: str | None = None

    #: Units held. Non-negative; fractional shares are common, hence ``Decimal``.
    quantity: Money = Field(ge=0)
    #: Price per unit, if known. Non-negative.
    current_unit_price: Money | None = Field(default=None, ge=0)
    #: Total cost basis of the position, if known. Non-negative.
    cost_basis: Money | None = Field(default=None, ge=0)
    #: Current market value. Non-negative; derived from quantity × unit price
    #: when not supplied directly (see validator).
    market_value: Money | None = Field(default=None, ge=0)

    currency: CurrencyCode
    as_of: AwareDatetime

    @model_validator(mode="after")
    def _derive_market_value(self) -> InvestmentHolding:
        """Fill in ``market_value`` from quantity × unit price when it's missing.

        If neither a market value nor a unit price is given we can't determine
        the position's worth, which is an incomplete holding — reject it.
        """

        if self.market_value is None:
            if self.current_unit_price is None:
                raise ValueError("market_value is required when current_unit_price is not provided")
            # Bypass re-validation; the computed value is correct by construction.
            object.__setattr__(
                self,
                "market_value",
                (self.quantity * self.current_unit_price).quantize(Decimal("0.0001")),
            )
        return self
