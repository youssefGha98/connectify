from typing import List, Dict

from ICO_distribution import ICOOrchestrator
from Liquidity_pool import LiquidityPool


class TokenEconomySimulator:
    def __init__(
        self,
        orchestrator: ICOOrchestrator,
        liquidity_pool: LiquidityPool,
        columns_to_exclude: List[str],
    ):
        """Initializes the simulator with necessary components and state variables."""
        self.orchestrator = orchestrator
        self.liquidity_pool = liquidity_pool
        self.columns_to_exclude = columns_to_exclude
        self.reset_state()

    def reset_state(self):
        """Resets or initializes the state for simulation."""
        self.tokens_sold = [0]
        self.token_price = [self.liquidity_pool.calculate_price()]
        self.usdc_to_buy_list = [0]
        self.price_after_mitigation = [0]

    def compute_monthly_released_tokens(self):
        """Computes the monthly released tokens from the orchestrator data, excluding specified columns."""
        df = self.orchestrator.create_participants_distribution_dataframe()
        self.monthly_release_tokens = df[
            df.columns.difference(self.columns_to_exclude)
        ].sum(axis=1)

    def compute_and_sell_token_substep(
        self, released_tokens: float, average_selling_order: float
    ):
        """Handles the token selling sub-step and returns transaction details."""
        price_before_selling = self.liquidity_pool.calculate_price()
        tokens_to_sell = min(
            released_tokens, average_selling_order / price_before_selling
        )
        self.liquidity_pool.sell_tokens(tokens_to_sell)
        price_after_selling = self.liquidity_pool.calculate_price()
        price_impact = (
            price_after_selling - price_before_selling
        ) / price_before_selling

        return tokens_to_sell, price_after_selling, price_impact, price_before_selling

    def compute_usdcs_to_buy_and_mitigate(
        self,
        price_impact: float,
        max_price_impact: float,
        with_mitigation: bool,
        price_before_selling: float,
    ):
        """Determines USDC purchase and price mitigation strategies based on price impact."""
        if abs(price_impact) > max_price_impact:
            usdc_to_buy = self.liquidity_pool.maintain_price(
                price_before_selling, max_price_impact
            )
            if with_mitigation:
                self.liquidity_pool.buy_tokens(usdc_to_buy)
            new_mitigated_price = self.liquidity_pool.calculate_price()
            return usdc_to_buy, new_mitigated_price
        else:
            return 0, self.liquidity_pool.calculate_price()

    def execute_transaction_step(
        self,
        released_tokens: float,
        average_selling_order: float,
        max_price_impact: float,
        with_mitigation: bool,
    ):
        """Executes a full transaction step including selling and potential mitigation."""
        while released_tokens > 0:
            tokens_to_sell, price_after_selling, price_impact, price_before_selling = (
                self.compute_and_sell_token_substep(
                    released_tokens, average_selling_order
                )
            )
            self.tokens_sold.append(tokens_to_sell)
            self.token_price.append(price_after_selling)
            usdcs_to_buy, new_mitigated_price = self.compute_usdcs_to_buy_and_mitigate(
                price_impact, max_price_impact, with_mitigation, price_before_selling
            )
            self.price_after_mitigation.append(new_mitigated_price)
            self.usdc_to_buy_list.append(usdcs_to_buy)
            released_tokens -= tokens_to_sell
            if tokens_to_sell < 1e-6:
                break

    def get_transaction_summary(self) -> Dict[str, List[float]]:
        """Returns a summary of transactions."""
        return {
            "tokens_sold": self.tokens_sold,
            "token_price": self.token_price,
            "usdcs_to_buy": self.usdc_to_buy_list,
            "price_after_mitigation": self.price_after_mitigation,
        }

    def run_vesting_simulation(
        self,
        average_selling_order: float,
        max_price_impact: float,
        with_mitigation: bool,
    ) -> Dict[str, List[float]]:
        """Runs the full vesting simulation over all monthly release tokens."""
        result = {
            "tokens_sold": [],
            "token_price": [],
            "usdcs_to_buy": [],
            "price_after_mitigation": [],
        }
        for released_tokens in self.monthly_release_tokens:
            self.reset_state()
            self.execute_transaction_step(
                released_tokens,
                average_selling_order,
                max_price_impact,
                with_mitigation=with_mitigation,
            )
            step_summary = self.get_transaction_summary()
            result["tokens_sold"].append(sum(step_summary["tokens_sold"]))
            result["usdcs_to_buy"].append(sum(step_summary["usdcs_to_buy"]))
            result["token_price"].append(step_summary["token_price"][-1])
            result["price_after_mitigation"].append(
                step_summary["price_after_mitigation"][-1]
            )
        return result
