from datetime import datetime, timedelta

from app.constants.enums import WithdrawalStatus
from app.repositories.user_repository import UserRepository
from app.repositories.withdrawal_repository import WithdrawalRepository
from app.services.wallet_service import WalletService


class WithdrawalService:

    MIN_WITHDRAWAL_AMOUNT = 1000.0

    # A withdrawal in one of these states still holds money out of the
    # wallet, so it counts against the 24h limit and can be reversed.
    ACTIVE_STATUSES = [
        WithdrawalStatus.INITIATED.value,
        WithdrawalStatus.SUCCESS.value,
    ]

    # Terminal "money returned" states (Question 2).
    FAILED_STATUSES = [
        WithdrawalStatus.FAILED.value,
        WithdrawalStatus.CANCELLED.value,
        WithdrawalStatus.REJECTED.value,
    ]

    def __init__(self):
        self.user_repository = UserRepository()
        self.withdrawal_repository = WithdrawalRepository()
        self.wallet_service = WalletService()

    async def withdraw(
        self,
        user_id: str,
        amount: float,
    ):

        user = await self.user_repository.find_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        if amount < self.MIN_WITHDRAWAL_AMOUNT:
            raise ValueError(
                f"Minimum withdrawal amount is Rs.{self.MIN_WITHDRAWAL_AMOUNT}."
            )

        if user["withdrawable_balance"] < amount:
            raise ValueError("Insufficient wallet balance.")

        last_withdrawal = user.get("last_withdrawal_at")

        if (
            last_withdrawal
            and datetime.utcnow() - last_withdrawal < timedelta(hours=24)
        ):
            raise ValueError(
                "Withdrawal allowed only once every 24 hours."
            )

        # Debit first so a failure here never creates a withdrawal record
        # for money that was not actually reserved.
        await self.wallet_service.debit_balance(
            user_id,
            amount,
        )

        now = datetime.utcnow()

        withdrawal = {
            "user_id": user_id,
            "amount": amount,
            "status": WithdrawalStatus.SUCCESS.value,
            "created_at": now,
            "updated_at": now,
        }

        withdrawal_id = await self.withdrawal_repository.create(
            withdrawal
        )

        await self.user_repository.update_user(
            user_id,
            {
                "last_withdrawal_at": now,
                "updated_at": now,
            },
        )

        return {
            "withdrawal_id": withdrawal_id,
            "amount": amount,
            "status": WithdrawalStatus.SUCCESS.value,
        }

    async def update_withdrawal_status(
        self,
        withdrawal_id: str,
        new_status: WithdrawalStatus,
    ):
        """Question 2 - Failed Payout Recovery.

        Marking a withdrawal as FAILED / CANCELLED / REJECTED credits the
        amount back into the user's withdrawable balance and unlocks the
        24h window so they can withdraw again. The state transition is
        applied atomically so the refund can happen at most once, even if
        this endpoint is called repeatedly.
        """

        target = new_status.value if isinstance(
            new_status, WithdrawalStatus
        ) else new_status

        withdrawal = await self.withdrawal_repository.find_by_id(
            withdrawal_id
        )

        if not withdrawal:
            raise ValueError("Withdrawal not found.")

        current = withdrawal["status"]

        if current == target:
            # Idempotent no-op.
            return {
                "withdrawal_id": withdrawal_id,
                "status": target,
                "refunded": False,
            }

        if current in self.FAILED_STATUSES:
            raise ValueError(
                "Withdrawal is already in a terminal state "
                "and cannot be updated."
            )

        # current is an ACTIVE status from here on.
        refunded = False

        if target in self.FAILED_STATUSES:

            won = await self.withdrawal_repository.transition_status_if_current(
                withdrawal_id,
                target,
                self.ACTIVE_STATUSES,
            )

            if not won:
                # Another concurrent call already reversed it.
                raise ValueError(
                    "Withdrawal is already in a terminal state "
                    "and cannot be updated."
                )

            await self.wallet_service.credit_balance(
                withdrawal["user_id"],
                withdrawal["amount"],
            )

            await self._unlock_withdrawal_window(withdrawal["user_id"])

            refunded = True

        else:
            # ACTIVE -> ACTIVE (e.g. INITIATED -> SUCCESS): no money moves.
            await self.withdrawal_repository.update_withdrawal_status(
                withdrawal_id,
                target,
            )

        return {
            "withdrawal_id": withdrawal_id,
            "status": target,
            "amount": withdrawal["amount"],
            "refunded": refunded,
        }

    async def _unlock_withdrawal_window(self, user_id: str):
        """Recompute the 24h lock from the remaining active withdrawals.

        After a payout is reversed, the failed withdrawal must not count
        against the once-per-24h limit, so the lock is pinned to the next
        most recent still-active withdrawal (or cleared entirely).
        """

        last_active = await self.withdrawal_repository.get_last_active_withdrawal(
            user_id,
            self.ACTIVE_STATUSES,
        )

        new_last = last_active["created_at"] if last_active else None

        await self.user_repository.update_user(
            user_id,
            {
                "last_withdrawal_at": new_last,
                "updated_at": datetime.utcnow(),
            },
        )

    async def get_user_withdrawals(
        self,
        user_id: str,
    ):

        user = await self.user_repository.find_by_id(user_id)

        if not user:
            raise ValueError("User not found.")

        withdrawals = await self.withdrawal_repository.get_user_withdrawals(
            user_id
        )

        for withdrawal in withdrawals:
            withdrawal["id"] = str(withdrawal["_id"])
            withdrawal.pop("_id")

        return withdrawals
