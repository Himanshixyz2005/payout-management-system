"""Integration tests for the Payout Management System.

Runs the real services against an isolated MongoDB database and asserts
the business rules from the assignment end to end:

  * Advance payout = 10% of earnings, idempotent across repeated runs.
  * Reconciliation: Approved -> earnings - advance, Rejected -> recover advance.
  * The assignment's worked example (3 x Rs.40 -> final payout Rs.68).
  * Withdrawal: minimum amount + one-per-24h restriction.
  * Question 2: failed payout recovery credits the amount back and unlocks
    re-withdrawal, and never double-refunds.

Requires a local MongoDB. Run with:

    python tests/test_payout_flow.py
"""
import asyncio
import os
import sys

# Isolate a throwaway database BEFORE importing the app (load_dotenv does
# not override an already-set env var).
os.environ["DATABASE_NAME"] = "payout_management_pytest"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import client  # noqa: E402
from app.services.user_service import UserService  # noqa: E402
from app.services.sale_service import SaleService  # noqa: E402
from app.services.wallet_service import WalletService  # noqa: E402
from app.services.advance_payout_service import AdvancePayoutService  # noqa: E402
from app.services.reconciliation_service import ReconciliationService  # noqa: E402
from app.services.withdrawal_service import WithdrawalService  # noqa: E402
from app.repositories.payout_repository import PayoutRepository  # noqa: E402
from app.constants.enums import (  # noqa: E402
    PayoutType,
    PayoutStatus,
    SaleStatus,
    WithdrawalStatus,
)

DB_NAME = "payout_management_pytest"
FAILURES = []


def expect(name, cond, info=""):
    mark = "OK  " if cond else "FAIL"
    print(f"  [{mark}] {name}" + (f"  ({info})" if info else ""))
    if not cond:
        FAILURES.append(name)


async def test_assignment_example():
    """3 sales of Rs.40 -> advance Rs.12; reconcile [rejected, approved,
    approved] -> wallet ends at Rs.80, reconciliation net = Rs.68."""
    print("\n== assignment example (Rs.40 x 3) ==")

    users = UserService()
    sales = SaleService()
    wallet = WalletService()
    advance = AdvancePayoutService()
    recon = ReconciliationService()
    payouts = PayoutRepository()

    user = await users.create_user("john_doe")
    uid = user["id"]

    sale_ids = []
    for _ in range(3):
        s = await sales.create_sale(uid, "brand_1", 40.0)
        sale_ids.append(s["id"])

    # Advance payout: 10% of 120 = 12.
    r1 = await advance.process_advance_payouts()
    expect("advance processed 3 sales", r1["processed_sales"] == 3, r1)
    expect("advance total = 12", r1["total_amount_paid"] == 12.0, r1)
    expect("balance after advance = 12", await wallet.get_balance(uid) == 12.0)

    # Idempotency: running again pays nothing more.
    r2 = await advance.process_advance_payouts()
    expect("advance idempotent (0 second run)", r2["processed_sales"] == 0, r2)
    expect("balance still 12 after re-run", await wallet.get_balance(uid) == 12.0)

    # Reconcile: first rejected, other two approved.
    await recon.reconcile_sale(sale_ids[0], SaleStatus.REJECTED)
    await recon.reconcile_sale(sale_ids[1], SaleStatus.APPROVED)
    await recon.reconcile_sale(sale_ids[2], SaleStatus.APPROVED)

    balance = await wallet.get_balance(uid)
    expect("wallet balance = 80 (2 approved x 40)", balance == 80.0, balance)

    # Reconciliation-phase net payout = final payouts - recovery = 72 - 4 = 68.
    docs = await payouts.get_user_payouts(uid)
    final_sum = sum(
        d["amount"] for d in docs if d["type"] == PayoutType.FINAL.value
    )
    recovery_sum = sum(
        d["amount"] for d in docs
        if d["type"] == PayoutType.ADJUSTMENT.value
        and d["status"] == PayoutStatus.SUCCESS.value
    )
    expect("final payouts sum = 72", final_sum == 72.0, final_sum)
    expect("recovery sum = 4", recovery_sum == 4.0, recovery_sum)
    expect(
        "reconciliation net payout = 68 (final - recovery)",
        final_sum - recovery_sum == 68.0,
        final_sum - recovery_sum,
    )

    # Cannot reconcile an already-reconciled sale.
    try:
        await recon.reconcile_sale(sale_ids[0], SaleStatus.APPROVED)
        expect("double reconcile rejected", False)
    except ValueError:
        expect("double reconcile rejected", True)


async def test_withdrawal_and_recovery():
    """24h restriction + Question 2 failed payout recovery."""
    print("\n== withdrawal + failed payout recovery (Q2) ==")

    users = UserService()
    wallet = WalletService()
    withdrawals = WithdrawalService()

    user = await users.create_user("jane_doe")
    uid = user["id"]

    # Fund the wallet directly to exceed the Rs.1000 minimum.
    await wallet.credit_balance(uid, 20000.0)

    # Below-minimum withdrawal is rejected.
    try:
        await withdrawals.withdraw(uid, 500.0)
        expect("below-minimum withdrawal rejected", False)
    except ValueError as e:
        expect("below-minimum withdrawal rejected", "Minimum" in str(e))

    # First valid withdrawal succeeds.
    w = await withdrawals.withdraw(uid, 5000.0)
    wid = w["withdrawal_id"]
    expect("withdrawal status SUCCESS", w["status"] == WithdrawalStatus.SUCCESS.value)
    expect("balance debited to 15000", await wallet.get_balance(uid) == 15000.0)

    # Second withdrawal inside 24h is blocked.
    try:
        await withdrawals.withdraw(uid, 5000.0)
        expect("second withdrawal within 24h blocked", False)
    except ValueError as e:
        expect("second withdrawal within 24h blocked", "24 hours" in str(e))

    # Q2: mark the payout FAILED -> amount credited back, lock cleared.
    res = await withdrawals.update_withdrawal_status(wid, WithdrawalStatus.FAILED)
    expect("failed payout refunded flag", res["refunded"] is True, res)
    expect("balance restored to 20000", await wallet.get_balance(uid) == 20000.0)

    # Idempotency: marking FAILED again must NOT refund a second time.
    try:
        res2 = await withdrawals.update_withdrawal_status(wid, WithdrawalStatus.FAILED)
        expect("repeat FAILED is no-op (no double refund)", res2["refunded"] is False, res2)
    except ValueError:
        # Also acceptable: terminal-state rejection, as long as no refund happened.
        expect("repeat FAILED is no-op (no double refund)", True)
    expect("balance still 20000 (no double refund)", await wallet.get_balance(uid) == 20000.0)

    # Re-withdrawal is now allowed (lock was cleared by the failure).
    w2 = await withdrawals.withdraw(uid, 5000.0)
    expect("re-withdrawal allowed after failure", w2["status"] == WithdrawalStatus.SUCCESS.value)
    expect("balance debited again to 15000", await wallet.get_balance(uid) == 15000.0)


async def main():
    await client.drop_database(DB_NAME)
    try:
        await test_assignment_example()
        await test_withdrawal_and_recovery()
    finally:
        await client.drop_database(DB_NAME)

    print("\n== summary ==")
    if FAILURES:
        print(f"FAILED {len(FAILURES)} check(s): {FAILURES}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
