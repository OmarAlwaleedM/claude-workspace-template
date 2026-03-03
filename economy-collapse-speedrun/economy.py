import config


class Economy:
    def __init__(self):
        self.gdp = config.STARTING_GDP
        self.employment = config.STARTING_EMPLOYMENT
        self.inflation = config.STARTING_INFLATION
        self.public_trust = config.STARTING_PUBLIC_TRUST
        self.trade_balance = config.STARTING_TRADE_BALANCE
        self.national_debt = config.STARTING_NATIONAL_DEBT
        self.destruction_score = 0

    def apply_policy(self, impacts: dict):
        self.gdp = self._clamp(self.gdp + impacts.get("gdp", 0))
        self.employment = self._clamp(self.employment + impacts.get("employment", 0))
        self.inflation = self._clamp(self.inflation + impacts.get("inflation", 0))
        self.public_trust = self._clamp(self.public_trust + impacts.get("public_trust", 0))
        self.trade_balance = self._clamp(self.trade_balance + impacts.get("trade_balance", 0))
        self.national_debt = self._clamp(self.national_debt + impacts.get("national_debt", 0))

    def add_destruction_points(self, points: int):
        self.destruction_score += points

    def get_state(self) -> dict:
        return {
            "gdp": self.gdp,
            "employment": self.employment,
            "inflation": self.inflation,
            "public_trust": self.public_trust,
            "trade_balance": self.trade_balance,
            "national_debt": self.national_debt,
        }

    def get_destruction_score(self) -> int:
        return self.destruction_score

    def is_collapsed(self) -> bool:
        return self.gdp < 10 or self.employment < 10

    @staticmethod
    def _clamp(value: int) -> int:
        return max(0, min(100, int(value)))
