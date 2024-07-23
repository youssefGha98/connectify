from dataclasses import dataclass
import math


@dataclass
class LiquidityPool:
    usdc_reserve: float
    token_reserve: float

    def calculate_price(self):
        return self.usdc_reserve / self.token_reserve

    def sell_tokens(self, tokens_sold):
        k = self.usdc_reserve * self.token_reserve
        self.token_reserve += tokens_sold
        self.usdc_reserve = k / self.token_reserve

    def buy_tokens(self, usdc_spent):
        k = self.usdc_reserve * self.token_reserve
        self.usdc_reserve += usdc_spent
        self.token_reserve = k / self.usdc_reserve

    def maintain_price(self, old_price, target_threshhold):
        token_reserve = self.token_reserve
        usdc_reserve = self.usdc_reserve
        k = token_reserve * usdc_reserve
        target_price = old_price * (1 + target_threshhold)
        new_usdc_reserve = math.sqrt(k * target_price)
        usdc_to_buy = new_usdc_reserve - usdc_reserve
        return usdc_to_buy
