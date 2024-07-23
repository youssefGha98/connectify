from itertools import accumulate

import pandas as pd


class StakingCalculator:
    def __init__(
        self, debt_usd: list, revenue: list, token_price: list, yearly_target_apr: float
    ):
        self.debt_usd = debt_usd
        self.revenue = revenue
        self.token_price = token_price
        self.yearly_target_apr = yearly_target_apr

    def compute_tokens_to_be_staked(self, proportion_of_tokens_to_be_staked):
        earnings = [r - d for r, d in zip(self.revenue, self.debt_usd)]
        earning_in_tokens = [e / p for e, p in zip(earnings, self.token_price)]
        tokens_to_buy = [-e for e in earning_in_tokens]
        tokens_to_be_staked_inflationary = [
            t * proportion_of_tokens_to_be_staked if t > 0 else 0 for t in tokens_to_buy
        ]
        tokens_to_be_bought_aligned = [
            -t * proportion_of_tokens_to_be_staked if t < 0 else 0
            for t in tokens_to_buy
        ]
        return tokens_to_be_staked_inflationary, tokens_to_be_bought_aligned

    def compute_incentive_for_stakers(
        self, proportion_of_tokens_to_be_staked, total_supply, initial_staking_pool
    ):
        monthly_target_apr = self.yearly_target_apr / 12
        tokens_to_be_staked_inflationary, tokens_to_be_bought_aligned = (
            self.compute_tokens_to_be_staked(proportion_of_tokens_to_be_staked)
        )
        incentive_for_stakers = list(
            accumulate(t * monthly_target_apr for t in tokens_to_be_staked_inflationary)
        )
        data = pd.DataFrame()
        data["incentive_for_stakers_0"] = incentive_for_stakers
        for i in range(1, 6):
            data[f"incentive_for_stakers_{i}"] = (
                data[f"incentive_for_stakers_{i-1}"] * monthly_target_apr
            )
            data["incentive_for_stakers_0"] += data[f"incentive_for_stakers_{i}"]
        staking_pool = [initial_staking_pool - data["incentive_for_stakers_0"][0]]
        for cumulative_incentive in data["incentive_for_stakers_0"][1:]:
            new_staking_pool_value = staking_pool[-1] - cumulative_incentive
            staking_pool.append(new_staking_pool_value)
        data["tokens_to_be_staked_inflationary"] = (
            data["incentive_for_stakers_0"] / self.yearly_target_apr
        )
        data["percent_staked"] = data["tokens_to_be_staked_inflationary"] / total_supply
        data["tokens_to_be_bought_aligned"] = tokens_to_be_bought_aligned
        data["staking_pool"] = staking_pool
        return data
