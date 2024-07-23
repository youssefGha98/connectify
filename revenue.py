from abc import ABC, abstractmethod
from typing import List
import numpy as np


class RevenueSource(ABC):
    @abstractmethod
    def calculate_revenues(self) -> List[float]:
        """Generate a list of total revenues over time or scenarios."""
        pass

    @abstractmethod
    def calculate_immediate_revenues(self) -> List[float]:
        """Calculate the immediate revenues over time or scenarios."""
        pass

    @abstractmethod
    def calculate_reserve_revenues(self) -> List[float]:
        """Calculate the reserve revenues over time or scenarios."""
        pass

    @abstractmethod
    def calculate_tokens_to_be_locked(self) -> List[float]:
        """Calculate the number of tokens to be locked over time or scenarios."""
        pass


class CostSource(ABC):
    @abstractmethod
    def calculate_costs(self) -> List[float]:
        """Generate a list of costs over time or scenarios."""
        pass


class FinancialCalculator:
    def __init__(self):
        self.revenue_sources: List[RevenueSource] = []
        self.cost_sources: List[CostSource] = []
        self.tokens_locked_history: List[float] = []

    def add_revenue_source(self, source: RevenueSource):
        """Adds a new revenue source to the calculator."""
        self.revenue_sources.append(source)

    def add_cost_source(self, source: CostSource):
        """Adds a new cost source to the calculator."""
        self.cost_sources.append(source)

    def total_revenues(self) -> List[float]:
        """Calculates and returns the total revenues from all sources across all periods."""
        if not self.revenue_sources:
            return []

        total = [0] * len(self.revenue_sources[0].calculate_revenues())
        for source in self.revenue_sources:
            revenues = source.calculate_revenues()
            total = [t + r for t, r in zip(total, revenues)]
        return total

    def total_immediate_revenues(self) -> List[float]:
        """Calculates and returns the total immediate revenues from all sources across all periods."""
        if not self.revenue_sources:
            return []

        total = [0] * len(self.revenue_sources[0].calculate_immediate_revenues())
        for source in self.revenue_sources:
            immediate_revenues = source.calculate_immediate_revenues()
            total = [t + ir for t, ir in zip(total, immediate_revenues)]
        return total

    def total_reserve_revenues(self) -> List[float]:
        """Calculates and returns the total reserve revenues from all sources across all periods."""
        if not self.revenue_sources:
            return []

        total = [0] * len(self.revenue_sources[0].calculate_reserve_revenues())
        for source in self.revenue_sources:
            reserve_revenues = source.calculate_reserve_revenues()
            total = [t + rr for t, rr in zip(total, reserve_revenues)]
        return total

    def total_tokens_locked(self) -> List[float]:
        """Calculates and returns the total tokens to be locked from all sources across all periods."""
        if not self.revenue_sources:
            return []

        total = [0] * len(self.revenue_sources[0].calculate_tokens_to_be_locked())
        for source in self.revenue_sources:
            tokens = source.calculate_tokens_to_be_locked()
            total = [t + tk for t, tk in zip(total, tokens)]
        return total

    def total_costs(self) -> List[float]:
        """Calculates and returns the total costs from all sources across all periods."""
        if not self.cost_sources:
            return []

        total = [0] * len(self.cost_sources[0].calculate_costs())
        for source in self.cost_sources:
            costs = source.calculate_costs()
            total = [t + c for t, c in zip(total, costs)]
        return total

    def net_earnings(self) -> List[float]:
        """Calculates and returns the net earnings (revenue minus costs) across all periods."""
        revenues = self.total_revenues()
        costs = self.total_costs()
        return [r - c for r, c in zip(revenues, costs)]

    def tokens_to_be_unlocked(self) -> List[float]:
        """Calculates and returns the tokens to be unlocked over time."""
        all_tokens_to_be_unlocked = []
        for source in self.revenue_sources:
            tokens_locked = source.calculate_tokens_to_be_locked()
            unlocking_duration = source.locking_duration
            tokens_unlocked = compute_tokens_to_be_unlocked(
                tokens_locked, unlocking_duration
            )
            all_tokens_to_be_unlocked = (
                [sum(x) for x in zip(all_tokens_to_be_unlocked, tokens_unlocked)]
                if all_tokens_to_be_unlocked
                else tokens_unlocked
            )
        return all_tokens_to_be_unlocked

    def compute_locked_tokens_history(self) -> List[float]:
        tokens_locked = self.total_tokens_locked()
        tokens_unlocked = self.tokens_to_be_unlocked()
        locked_tokens_history = []
        current_locked = 0
        for locked, unlocked in zip(tokens_locked, tokens_unlocked):
            current_locked = current_locked + locked - unlocked
            locked_tokens_history.append(current_locked)
        self.tokens_locked_history = locked_tokens_history
        return locked_tokens_history


def compute_tokens_to_be_unlocked(
    tokens_to_be_locked: List[float], locking_duration: int
) -> List[float]:
    tokens_to_be_unlocked = [0] * (locking_duration + len(tokens_to_be_locked))
    for i, token in enumerate(tokens_to_be_locked):
        monthly_unlock = token / locking_duration
        for month in range(locking_duration):
            tokens_to_be_unlocked[i + month] += monthly_unlock
    return tokens_to_be_unlocked


class MonthlyCost(CostSource):
    def __init__(self, costs: List[float]):
        self.costs = costs

    def calculate_costs(self) -> List[float]:
        return self.costs


class BaseRevenue(RevenueSource, ABC):
    def __init__(
        self,
        units: List[int],
        unit_price: float,
        proportion_immediate: float,
        token_price: List[float] = None,
        locking_duration: int = 12,
    ):
        self.units = units
        self.unit_price = unit_price
        self.proportion_immediate = proportion_immediate
        self.token_price = token_price or [1.0] * len(units)
        self.locking_duration = locking_duration

    def calculate_revenues(self) -> List[float]:
        return [float(unit * self.unit_price) for unit in self.units]

    def calculate_immediate_revenues(self) -> List[float]:
        return [
            float(revenue * self.proportion_immediate)
            for revenue in self.calculate_revenues()
        ]

    def calculate_reserve_revenues(self) -> List[float]:
        return [
            float(revenue * (1 - self.proportion_immediate))
            for revenue in self.calculate_revenues()
        ]

    def calculate_tokens_to_be_locked(self) -> List[float]:
        immediate_revenues = self.calculate_immediate_revenues()
        return [
            float(ir / token_price / self.locking_duration)
            for ir, token_price in zip(immediate_revenues, self.token_price)
        ]


class LicenseRevenue(BaseRevenue):
    def __init__(
        self,
        licenses: List[int],
        price_per_license: float,
        license_yearly_cost: float,
        proportion_immediate_revenue: float,
    ):
        super().__init__(
            licenses,
            price_per_license - license_yearly_cost,
            proportion_immediate_revenue,
            locking_duration=12,
        )


class DeviceCreationRevenue(BaseRevenue):
    def __init__(
        self,
        devices: List[int],
        price_per_device: float,
        proportion_immediate_revenue: float,
        token_price: List[float],
    ):
        super().__init__(
            devices,
            price_per_device,
            proportion_immediate_revenue,
            token_price,
            locking_duration=36,
        )


class MessageRevenue(BaseRevenue):
    def __init__(
        self, messages: List[int], price_per_message: float, token_price: List[float]
    ):
        super().__init__(
            messages, price_per_message, 0.0, token_price, locking_duration=12
        )


class ServicesRevenue(BaseRevenue):
    def __init__(
        self,
        objects: List[int],
        ping_wifi_proportion: List[float],
        instant_data_consult_proportion: List[float],
        data_storage_proportion: List[float],
        wifi_price: float,
        data_consult_price: float,
        data_storage_price: float,
        wifi_cost: float,
        data_consult_cost: float,
        data_storage_cost: float,
        proportion_immediate: float,
        token_price: List[float],
    ):
        super().__init__(
            objects, 1.0, 0.0, token_price
        )  # Price per object is calculated separately
        self.ping_wifi_proportion = ping_wifi_proportion
        self.instant_data_consult_proportion = instant_data_consult_proportion
        self.data_storage_proportion = data_storage_proportion
        self.wifi_price = wifi_price
        self.data_consult_price = data_consult_price
        self.data_storage_price = data_storage_price
        self.wifi_cost = wifi_cost
        self.data_consult_cost = data_consult_cost
        self.data_storage_cost = data_storage_cost

    def calculate_revenues(self) -> List[float]:
        revenue_wifi = [
            obj * prop * (self.wifi_price - self.wifi_cost)
            for obj, prop in zip(self.units, self.ping_wifi_proportion)
        ]
        revenue_data_consult = [
            obj * prop * (self.data_consult_price - self.data_consult_cost)
            for obj, prop in zip(self.units, self.instant_data_consult_proportion)
        ]
        revenue_data_storage = [
            obj * prop * (self.data_storage_price - self.data_storage_cost)
            for obj, prop in zip(self.units, self.data_storage_proportion)
        ]
        return [
            w + c + s
            for w, c, s in zip(revenue_wifi, revenue_data_consult, revenue_data_storage)
        ]

    def calculate_immediate_revenues(self) -> List[float]:
        return [0.0] * len(self.units)

    def calculate_reserve_revenues(self) -> List[float]:
        return self.calculate_revenues()


class NetworkRevenue(BaseRevenue):
    def __init__(
        self,
        light_objects: List[int],
        silver_objects: List[int],
        gold_objects: List[int],
        premium_objects: List[int],
        token_price: List[float],
        proportion_immediate: float,
    ):
        light_price, silver_price, gold_price, premium_price = 1.0, 3.0, 8.0, 12.0
        light_cost, silver_cost, gold_cost, premium_cost = 0.07, 1.08, 5.4, 10.8

        self.light_objects = light_objects
        self.silver_objects = silver_objects
        self.gold_objects = gold_objects
        self.premium_objects = premium_objects
        self.token_price = token_price
        self.proportion_immediate = proportion_immediate
        self.locking_duration = 12

        self.light_revenue = [
            float(obj * (light_price - light_cost)) for obj in light_objects
        ]
        self.silver_revenue = [
            float(obj * (silver_price - silver_cost)) for obj in silver_objects
        ]
        self.gold_revenue = [
            float(obj * (gold_price - gold_cost)) for obj in gold_objects
        ]
        self.premium_revenue = [
            float(obj * (premium_price - premium_cost)) for obj in premium_objects
        ]

        self.revenues = [
            l + s + g + p
            for l, s, g, p in zip(
                self.light_revenue,
                self.silver_revenue,
                self.gold_revenue,
                self.premium_revenue,
            )
        ]
        self.unit_price = (
            sum(self.revenues) / len(self.revenues) if self.revenues else 0.0
        )

    def calculate_revenues(self) -> List[float]:
        return self.revenues

    def calculate_immediate_revenues(self) -> List[float]:
        return [float(revenue * self.proportion_immediate) for revenue in self.revenues]

    def calculate_reserve_revenues(self) -> List[float]:
        return [
            float(revenue * (1 - self.proportion_immediate))
            for revenue in self.revenues
        ]

    def calculate_tokens_to_be_locked(self) -> List[float]:
        immediate_revenues = self.calculate_immediate_revenues()
        return [
            float(ir / token_price)
            for ir, token_price in zip(immediate_revenues, self.token_price)
        ]
