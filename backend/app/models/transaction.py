"""Transaction — a single money movement on an account.

Modeled on FDX's transaction shape, including its sign convention: the ``amount``
is an **unsigned** magnitude and ``debit_credit_memo`` carries the direction.
This avoids the perennial "is a negative amount a debit or a credit?" ambiguity
that bites aggregators merging feeds from many banks (Item 5's whole problem).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import AwareDatetime, model_validator

from .common import CurrencyCode, EntityId, FdxBaseModel, Money


class DebitCreditMemo(StrEnum):
    """Direction of the money movement, relative to the account.

    ``DEBIT`` reduces the account balance (a purchase, a withdrawal); ``CREDIT``
    increases it (a deposit, a refund).
    """

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class TransactionStatus(StrEnum):
    """Whether the transaction has settled."""

    PENDING = "PENDING"
    POSTED = "POSTED"


class Transaction(FdxBaseModel):
    """One transaction belonging to an account."""

    transaction_id: EntityId
    account_id: EntityId

    #: Unsigned magnitude of the movement; direction lives in
    #: ``debit_credit_memo``. Must be strictly positive — a zero-value
    #: transaction is meaningless and almost always a parsing artifact.
    amount: Money
    currency: CurrencyCode
    debit_credit_memo: DebitCreditMemo

    status: TransactionStatus = TransactionStatus.POSTED

    #: When the transaction occurred (initiated). Always present.
    transaction_timestamp: AwareDatetime
    #: When it settled. Present iff ``status`` is ``POSTED``.
    posted_timestamp: AwareDatetime | None = None

    description: str | None = None
    memo: str | None = None
    #: Free-form category label (e.g. "Groceries"). Categorization schemes vary
    #: by source; we keep it as an opaque string at this layer.
    category: str | None = None
    payee: str | None = None

    @model_validator(mode="after")
    def _amount_positive(self) -> Transaction:
        if self.amount <= 0:
            raise ValueError(
                "transaction amount must be positive (direction lives in debit_credit_memo)"
            )
        return self

    @model_validator(mode="after")
    def _posted_timestamp_consistent(self) -> Transaction:
        """Tie ``posted_timestamp`` to settlement status.

        A POSTED transaction must say when it posted; a PENDING one hasn't posted
        yet, so a posted timestamp would be contradictory.
        """

        if self.status is TransactionStatus.POSTED and self.posted_timestamp is None:
            raise ValueError("a POSTED transaction requires a posted_timestamp")
        if self.status is TransactionStatus.PENDING and self.posted_timestamp is not None:
            raise ValueError("a PENDING transaction must not have a posted_timestamp")
        return self
