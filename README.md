# Payout Management System

This is a working payout system for **affiliate sales** — it handles the whole
money journey: paying users an advance up front, reconciling each sale once it's
approved or rejected, tracking wallet balances, letting users withdraw, and
clawing back money when a payout falls through.

It's built on **FastAPI** (fully async) with **MongoDB** underneath via Motor.

---

## Table of Contents

1. [What it does & the rules](#1-what-it-does--the-rules)
2. [How it's put together](#2-how-its-put-together)
3. [Data Model & Schema](#3-data-model--schema)
4. [The classes](#4-the-classes)
5. [API Reference](#5-api-reference)
6. [The main workflows](#6-the-main-workflows)
7. [Edge cases & things that can go wrong](#7-edge-cases--things-that-can-go-wrong)
8. [Why it's built this way](#8-why-its-built-this-way)
9. [Getting it running](#9-getting-it-running)
10. [Testing](#10-testing)

---

## 1. What it does & the rules

Every sale starts life as **`pending`**. The system pays out an **advance worth
10% of the earnings** on sales that qualify, and later an admin **reconciles**
each one — marking it `approved` or `rejected`. That's when the **final payout**
gets settled, minus whatever advance was already handed over.

Here are the rules that drive all of it:

| Rule | What happens |
|------|--------------|
| **Advance payout** | Each `pending` sale earns a one-time advance of 10%. Run the advance job as many times as you like — the same sale never gets paid twice. |
| **Approved sale** | Final payout = `earning − advance_paid`. So a ₹30 sale with a ₹3 advance already paid leaves ₹27 to credit. |
| **Rejected sale** | The advance was never really earned, so we take it back: adjustment = `−advance_paid`. A ₹50 sale with a ₹5 advance means −₹5. |
| **Withdrawal limit** | Users can withdraw **once every 24 hours** at most, and never less than ₹1000 at a time. |
| **Failed payout recovery (Q2)** | If a payout to the user later comes back as `cancelled`, `rejected`, or `failed`, the money goes **back into their withdrawable balance** so they can withdraw it again. |

### A worked example (straight from the assignment)

Say `john_doe` has 3 sales of ₹40 each:

- The pending earnings add up to ₹120, so the **advance is ₹12** — ₹4 per sale.
- They get reconciled as `[rejected, approved, approved]`.

| Sale | Earnings | Advance | Final adjustment |
|------|----------|---------|------------------|
| Rejected | 40 | 4 | **−4** |
| Approved | 40 | 4 | **36** |
| Approved | 40 | 4 | **36** |

**The reconciliation phase pays out −4 + 36 + 36 = ₹68.** Add the ₹12 advance
that already went out, and the wallet lands on **₹80** — exactly the earnings of
the two approved sales, with the rejected one netting out to zero. The whole
thing is checked end-to-end in
[`tests/test_payout_flow.py`](tests/test_payout_flow.py).

---

## 2. How it's put together

It's a straightforward layered setup, which keeps the HTTP handling, the
business rules, and the database work separate and easy to test on their own:

```
             HTTP request
                  │
   ┌──────────────▼──────────────┐
   │  API layer  (app/api)       │  FastAPI routers: validation via
   │                             │  Pydantic schemas, maps ValueError
   │                             │  → HTTP 400 / 404
   └──────────────┬──────────────┘
                  │
   ┌──────────────▼──────────────┐
   │  Service layer (app/services)│ Business rules & orchestration.
   │                             │  Raises ValueError on rule violations.
   └──────────────┬──────────────┘
                  │
   ┌──────────────▼──────────────┐
   │  Repository layer            │ BaseRepository CRUD + per-collection
   │  (app/repositories)          │ queries. Only layer that talks Mongo.
   └──────────────┬──────────────┘
                  │
              MongoDB (Motor async driver)
```

A few supporting pieces round it out:

- **Schemas** (`app/schemas`) — the Pydantic request/response models.
- **Constants/Enums** (`app/constants`) — `SaleStatus`, `PayoutType`,
  `PayoutStatus`, `WithdrawalStatus`.
- **Config/DB** (`app/core`, `app/database`) — env-driven settings and the
  shared async Mongo client.

**Why bother with layers?** Because the business rules never touch FastAPI or
Mongo directly. That means you can unit- and integration-test them by pointing
the services at a throwaway database (which is exactly what the test suite
does), and you could swap out the database entirely without rewriting a single
rule.

---

## 3. Data Model & Schema

There are four collections. IDs are Mongo `ObjectId`s internally, but they come
back as a plain string `id` in responses.

### `users`
| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | PK |
| `username` | string | **unique** (enforced in the service) |
| `withdrawable_balance` | float | the wallet balance |
| `last_withdrawal_at` | datetime \| null | drives the 24h lock |
| `created_at`, `updated_at` | datetime | |

### `sales`
| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | PK |
| `user_id` | string | → `users._id` |
| `brand` | string | |
| `earning` | float | > 0 |
| `status` | enum | `pending` → `approved` / `rejected` |
| `advance_paid` | bool | the idempotency guard for advances |
| `advance_amount` | float | how much advance actually went out |
| `created_at`, `updated_at` | datetime | |

### `payouts` (the ledger of every money movement)
| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | PK |
| `user_id`, `sale_id` | string | references |
| `amount` | float | |
| `type` | enum | `advance` / `final` / `adjustment` |
| `status` | enum | `success` / `failed` / `pending` |
| `created_at` | datetime | |

### `withdrawals`
| Field | Type | Notes |
|-------|------|-------|
| `_id` | ObjectId | PK |
| `user_id` | string | → `users._id` |
| `amount` | float | |
| `status` | enum | `initiated` / `success` / `failed` / `cancelled` / `rejected` |
| `created_at`, `updated_at` | datetime | |

### How they relate, and the indexes to add

```
users 1───* sales 1───* payouts
users 1───* withdrawals
```

- `users.username` — a **unique index** to back up the app-level uniqueness
  check against race conditions.
- `sales.user_id`, `sales.{status, advance_paid}` — for the advance job and
  per-user queries.
- `payouts.user_id`, `payouts.sale_id` — for ledger lookups.
- `withdrawals.{user_id, created_at}` — for finding the most recent withdrawal.

---

## 4. The classes

| Class | What it's responsible for |
|-------|----------------|
| `BaseRepository` | Generic async CRUD (`create`, `find_by_id`, `find_one`, `find_many`, `update`, `delete`) with safe `ObjectId` parsing. |
| `UserRepository` / `SaleRepository` / `PayoutRepository` / `WithdrawalRepository` | Collection-specific queries built on top of `BaseRepository`. |
| `UserService` | Creating and fetching users, plus wallet-balance bookkeeping. |
| `SaleService` | Creating sales, listing them by user, and guarded status updates. |
| `WalletService` | `credit_balance` / `debit_balance` with validation — the one and only place a balance ever changes. |
| `AdvancePayoutService` | The idempotent 10% advance job over pending sales. |
| `ReconciliationService` | Approved → final payout; rejected → advance recovery. |
| `WithdrawalService` | Withdrawals (the min + 24h rules) and the **Question 2** failed-payout recovery. |

Services lean on repositories (and `WalletService`) through composition, so
money only ever moves in one place: through `WalletService`.

---

## 5. API Reference

Base URL: `http://127.0.0.1:8000`  · Interactive docs live at `/docs`.

### Users
| Method | Path | Body | Success |
|--------|------|------|---------|
| `POST` | `/users/` | `{ "username": "john_doe" }` | 201 |
| `GET` | `/users/{user_id}` | — | 200 |
| `GET` | `/users/` | — | 200 |

### Sales
| Method | Path | Body | Success |
|--------|------|------|---------|
| `POST` | `/sales/` | `{ "user_id", "brand", "earning" }` | 201 |
| `GET` | `/sales/{sale_id}` | — | 200 |
| `GET` | `/sales/user/{user_id}` | — | 200 |
| `PATCH` | `/sales/{sale_id}` | `{ "status": "approved" }` | 200 |

### Advance Payouts
| Method | Path | Body | Success |
|--------|------|------|---------|
| `POST` | `/payouts/advance` | — | 200 → `{ processed_sales, total_amount_paid }` |

### Reconciliation
| Method | Path | Body | Success |
|--------|------|------|---------|
| `POST` | `/reconciliation/{sale_id}` | `{ "status": "approved" \| "rejected" }` | 200 |

### Wallet
| Method | Path | Success |
|--------|------|---------|
| `GET` | `/wallet/{user_id}` | 200 → `{ withdrawable_balance }` |

### Withdrawals
| Method | Path | Body | Success |
|--------|------|------|---------|
| `POST` | `/withdrawals/` | `{ "user_id", "amount" }` | 201 |
| `PATCH` | `/withdrawals/{withdrawal_id}/status` | `{ "status": "failed" }` | 200 → `{ ..., refunded }` **(Q2)** |
| `GET` | `/withdrawals/{user_id}` | — | 200 |

As for error codes: validation problems come back as **422**, broken business
rules as **400**, and anything that doesn't exist as **404**.

---

## 6. The main workflows

**Advance payout** (`POST /payouts/advance`)
1. Grab the pending sales where `advance_paid = false`.
2. For each one: credit `round(earning × 0.10, 2)`, write an `advance` payout,
   and set `advance_paid = true` along with `advance_amount`.
3. It's idempotent — that flag is what guarantees no sale gets paid twice, no
   matter how often the job runs.

**Reconciliation** (`POST /reconciliation/{sale_id}`)
- **Approved:** credit `earning − advance_amount` and write a `final` payout.
- **Rejected:** debit `advance_amount` to claw the advance back, and write an
  `adjustment` payout.
- Only `pending` sales can be reconciled, and once they are, the sale settles
  into its final status.

**Withdrawal + recovery**
- `POST /withdrawals/` → check it's ≥ ₹1000 and no more than once per 24h, debit
  the wallet, and record it as `success`.
- `PATCH /withdrawals/{id}/status` into a failure state → **put the money back**,
  clear the 24h lock, and let the user withdraw again (this is Question 2).

---

## 7. Edge cases & things that can go wrong

- **Running the advance job twice** — the `advance_paid` flag has it covered; a
  re-run pays out nothing.
- **Reconciling the same sale twice** — a sale that isn't `pending` gets a 400.
- **Not enough balance to recover** — if a rejected sale's advance can't be
  clawed back (the user already spent it), we record the recovery as a
  **`failed` adjustment** payout instead of crashing, and the sale still moves
  to `rejected`.
- **A bad `ObjectId`** — `BaseRepository` quietly returns `None`/`False` rather
  than throwing, which surfaces as a clean 404.
- **Withdrawals that are too small or too frequent** — these get explicit 400s.
- **Double-refunding a failed payout** — the status change goes through an
  **atomic conditional update** (`transition_status_if_current`), so only one
  caller can ever flip `active → failed`. The credit-back happens **at most
  once**, even if the call comes in repeatedly or concurrently — the repeats
  just come back with `refunded: false`.
- **The 24h lock after a failed payout** — it's recomputed from whatever active
  withdrawals remain, so a reversed payout never unfairly counts against the
  limit.
- **Input validation** — Pydantic checks types, `username` length, and that
  `earning`/`amount` are `> 0` before any business logic even starts.

---

## 8. Why it's built this way

- **Wallet as the source of truth, backed by a payout ledger.** The balance is
  a single mutable number, but every change also writes an immutable `payouts`
  row. That gives you a full audit trail — and it's how the "₹68" figure can be
  rebuilt from the ledger after the fact.
- **`ValueError` as the one business-error channel.** Services just raise a
  plain `ValueError`; the routers are what turn it into an HTTP response. This
  keeps the service layer framework-agnostic and easy to unit-test.
- **Idempotency comes from state, not job history.** Advances rely on a boolean
  flag; refunds rely on a conditional status transition. Both make the
  operations safe to retry — which really matters when you're moving money.
- **`user_id` is denormalised (a string) on sales and withdrawals** rather than
  doing DB-level joins. It fits MongoDB's document model and keeps reads to a
  single collection.
- **A known limitation: no multi-document transactions.** On a standalone Mongo,
  a credit and a status write are two separate operations. The refund path is
  hardened with an atomic conditional update so it can't double-pay, but a
  stricter production build would wrap the credit + ledger write in a real Mongo
  transaction (on a replica set), or use a per-payout idempotency key. Calling
  it out here rather than hiding it.
- **Naive UTC datetimes** (`datetime.utcnow()`) are used everywhere on purpose,
  so the 24h math never ends up mixing aware and naive values.

---

## 9. Getting it running

**You'll need:** Python 3.10+ and a MongoDB instance running on
`localhost:27017`.

```bash
# 1. create & activate a virtualenv (this is just one way)
python -m venv venv
venv\Scripts\activate         # Windows
# source venv/bin/activate    # macOS/Linux

# 2. install the dependencies
pip install -r requirements.txt

# 3. set up your environment: copy the example and tweak if needed
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
#    MONGODB_URI=mongodb://localhost:27017
#    DATABASE_NAME=payout_management

# 4. run the API
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/docs** for the interactive Swagger UI.

---

## 10. Testing

There's an end-to-end integration suite that runs the real services against an
**isolated test database** (`payout_management_pytest`, which gets dropped
automatically afterward). It checks every business rule — including the
assignment's ₹68 example and Question 2:

```bash
python tests/test_payout_flow.py
```

If everything's good, you'll see this at the end:

```
== summary ==
ALL CHECKS PASSED
```
