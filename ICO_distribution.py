from dataclasses import dataclass, field
from typing import List
import pandas as pd


@dataclass
class ICOParticipant:
    description: str
    percent_of_tot_supply: float
    price_per_token: float = 0.0
    tge_percent: float = 0.0
    cliff_months: int = 0
    distribution_months: int = 0

    total_supply: float = field(init=False)
    valuation: float = field(init=False)
    collected_usd: float = 0.0
    multiplier: float = 0.0
    distribution_plan: List[float] = field(init=False)

    def calculate_financials(self, total_ico_supply: float, listing_price: float):
        self.total_supply = self.percent_of_tot_supply / 100 * total_ico_supply
        self.valuation = listing_price * self.total_supply
        if self.price_per_token is not None:
            self.collected_usd = self.price_per_token * self.total_supply
            self.multiplier = (
                self.valuation / self.collected_usd if self.collected_usd != 0 else 0
            )
        self.distribution_plan = self.distribute_with_cliff()

    def distribute_with_cliff(self):
        distribution = [0] * (self.cliff_months + self.distribution_months + 1)
        tge_tokens = self.total_supply * (self.tge_percent / 100)
        remaining_tokens = self.total_supply - tge_tokens
        monthly_distribution = (
            remaining_tokens / self.distribution_months
            if self.distribution_months > 0
            else 0
        )

        distribution[0] = tge_tokens
        for i in range(
            self.cliff_months + 1, self.cliff_months + self.distribution_months + 1
        ):
            distribution[i] = monthly_distribution

        return distribution

    def to_dataframe(self):
        """Convert participant data (excluding distribution plan) to a pandas DataFrame."""
        data = {
            "Description": [self.description],
            "Total Supply": [self.total_supply],
            "Percent of Total Supply": [self.percent_of_tot_supply],
            "Price per Token": [self.price_per_token],
            "Valuation": [self.valuation],
            "Collected USD": [self.collected_usd],
            "Multiplier": [self.multiplier],
            "TGE": [self.tge_percent],
        }
        return pd.DataFrame(data)


@dataclass
class ICOOrchestrator:
    total_supply: float
    listing_price: float
    participants: List[ICOParticipant] = field(default_factory=list)

    def add_participant(self, participant: ICOParticipant):
        """Ajoute un participant à l'orchestrateur après avoir calculé ses finances."""
        participant.calculate_financials(self.total_supply, self.listing_price)
        self.participants.append(participant)

    def create_participants_financial_dataframe(self):
        """Crée un DataFrame consolidé des informations financières des participants."""
        data = {
            "Description": [p.description for p in self.participants],
            "Total Supply": [p.total_supply for p in self.participants],
            "Valuation": [p.valuation for p in self.participants],
            "Collected USD": [p.collected_usd for p in self.participants],
            "Multiplier": [p.multiplier for p in self.participants],
        }
        return pd.DataFrame(data)

    def extend_distribution_plan(self, participant: ICOParticipant, max_months: int):
        """Étend le plan de distribution d'un participant jusqu'à max_months."""
        if len(participant.distribution_plan) < max_months:
            participant.distribution_plan += [0] * (
                max_months - len(participant.distribution_plan)
            )

    def create_participants_distribution_dataframe(self):
        """Crée un DataFrame montrant la distribution de tokens pour chaque participant."""
        max_months = max(len(p.distribution_plan) for p in self.participants)
        for participant in self.participants:
            self.extend_distribution_plan(participant, max_months)
        data = {p.description: p.distribution_plan for p in self.participants}
        return pd.DataFrame(data)
