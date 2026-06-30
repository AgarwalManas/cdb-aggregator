"""Mock messy-schema data provider (Item 4).

A second standalone "bank" whose API looks nothing like FDX — a stand-in for a
legacy core-banking system you might otherwise have to screen-scrape. Its whole
job is to be *hard to map*, so the normalizer (Item 5) has to earn its keep.

Where the FDX bank (Item 3) is clean and standards-native, this one differs on
every axis on purpose:

============== ===================================== =============================
Aspect         Mock FDX bank (Item 3)                Legacy bank (this, Item 4)
============== ===================================== =============================
Auth           OAuth2 bearer + granular scopes       opaque session id, all-or-nothing
Shape          separate flat endpoints               one nested blob
Field names    FDX (``accountId``, ``amount``)       abbreviated (``acctRef``, ``amt``)
Money          JSON numbers                          strings with thousands commas
Txn direction  unsigned + ``debitCreditMemo``        signed amount (negative = debit)
Dates          ISO 8601 (``...Z``)                   epoch millis AND ``DD/MM/YYYY``
Currency       object ``{"currencyCode": "CAD"}``    bare lowercase ``"cad"``
Pending        ``status: "PENDING"``                 ``cleared: false``
============== ===================================== =============================

Run it on its own::

    uvicorn app.providers.legacy_bank.app:app --app-dir backend --port 9002
"""

from __future__ import annotations

from .app import app, create_app

__all__ = ["app", "create_app"]
