from typing import Dict


class Pool:
    def __init__(
        self, name: str, max_tokens: float = float("inf"), initial_tokens: float = 0.0
    ):
        self.name = name
        self.tokens_history = [initial_tokens]
        self.inflows = [0.0] * (
            1 if initial_tokens == 0 else 2
        )  # to match the history length
        self.outflows = [0.0] * (
            1 if initial_tokens == 0 else 2
        )  # to match the history length
        self.max_tokens = max_tokens

    def add_tokens(self, amount: float):
        self.inflows[-1] += amount

    def subtract_tokens(self, amount: float):
        self.outflows[-1] += amount

    def update_history(self):
        current_tokens = self.tokens_history[-1] + self.inflows[-1] - self.outflows[-1]
        current_tokens = min(max(current_tokens, 0), self.max_tokens)
        self.tokens_history.append(current_tokens)
        self.inflows.append(0.0)
        self.outflows.append(0.0)

    def get_current_tokens(self) -> float:
        return self.tokens_history[-1] if self.tokens_history else 0.0


def distribute_tokens_to_pools(
    monthly_unlocked_tokens: float, pools: Dict[str, Pool], ratios: Dict[str, float]
):
    for pool_name, ratio in ratios.items():
        pools[pool_name].add_tokens(monthly_unlocked_tokens * ratio)


def compute_incentive_emission(
    total_tokens_locked: float,
    pool_tokens: float,
    pool_max_tokens: float,
    emission_rate: float,
) -> float:
    proportional_emission_rate = pool_tokens / pool_max_tokens
    return total_tokens_locked * emission_rate * proportional_emission_rate
