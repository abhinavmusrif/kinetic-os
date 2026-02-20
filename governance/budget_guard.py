"""Budget enforcement utility."""

from __future__ import annotations


class BudgetGuard:
    """Tracks and enforces daily spend against policy budget."""

    def __init__(self, max_daily_budget_usd: float) -> None:
        self.max_daily_budget_usd = float(max_daily_budget_usd)
        self.spent_today_usd = 0.0

    def can_spend(self, amount_usd: float) -> bool:
        """Return whether spending amount stays within budget."""
        return self.spent_today_usd + amount_usd <= self.max_daily_budget_usd

    def charge(self, amount_usd: float) -> bool:
        """Charge amount if within budget and return success."""
        if not self.can_spend(amount_usd):
            return False
        self.spent_today_usd += amount_usd
        return True
