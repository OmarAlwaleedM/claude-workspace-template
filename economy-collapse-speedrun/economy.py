"""
economy.py — Economy simulation model.

This module simulates a fictional country's economy using 6 key indicators,
each on a 0-100 scale. Every round, the winning policy proposal's impacts
are applied to these indicators, changing the economy's state.

The 6 economic indicators are:
    - GDP (Gross Domestic Product): overall economic output (higher = better)
    - Employment: job availability (higher = better)
    - Inflation: rate of price increases (lower = better)
    - Public Trust: citizens' confidence in government (higher = better)
    - Trade Balance: exports vs imports (higher = better)
    - National Debt: government borrowing (lower = better)

Key design decisions:
    - Individual policy impacts are capped at +/-15 per indicator per round,
      preventing any single proposal from instantly collapsing the economy
    - All indicators are clamped to the 0-100 range
    - A cumulative "score" tracks total destruction/prosperity points across rounds
    - The economy is considered "collapsed" when GDP or employment hits 0,
      which triggers an early game over in destructive mode
"""

# Import the config module to access starting economy values
import config


class Economy:
    """
    Manages the 6-indicator economy state and a cumulative score.

    This class is the core simulation engine. Each round, the game calls
    apply_policy() with the AI-evaluated impacts of the winning proposal.
    The class ensures all values stay within valid bounds (0-100) and
    individual changes are capped at +/-15 per round.

    Attributes:
        gdp: Current GDP level (0-100)
        employment: Current employment level (0-100)
        inflation: Current inflation level (0-100, lower is better)
        public_trust: Current public trust level (0-100)
        trade_balance: Current trade balance (0-100)
        national_debt: Current national debt (0-100, lower is better)
        score: Cumulative points awarded by the AI across all rounds
    """

    def __init__(self):
        """
        Initialize the economy with starting values from config.py.

        These starting values represent a "decent but not perfect" economy,
        giving parliament room to either improve or destroy it.
        """
        self.gdp = config.STARTING_GDP                       # Start at 75
        self.employment = config.STARTING_EMPLOYMENT          # Start at 80
        self.inflation = config.STARTING_INFLATION            # Start at 20 (low = good)
        self.public_trust = config.STARTING_PUBLIC_TRUST      # Start at 70
        self.trade_balance = config.STARTING_TRADE_BALANCE    # Start at 60
        self.national_debt = config.STARTING_NATIONAL_DEBT    # Start at 30 (low = good)
        self.score = 0  # Cumulative score — tracks total destruction/prosperity points

    def apply_policy(self, impacts: dict):
        """
        Apply a winning policy's economic impacts to all 6 indicators.

        Each impact value is first capped to [-15, +15] (so no single policy
        can swing an indicator more than 15 points), then added to the current
        value, and finally clamped to [0, 100] to stay within bounds.

        Args:
            impacts: Dictionary with keys like "gdp", "employment", etc.
                     and integer values representing the change to apply.
                     Example: {"gdp": -10, "employment": -5, "inflation": 8}
        """
        # For each indicator: get the impact (default 0), cap it, add to current, clamp result
        self.gdp = self._clamp(self.gdp + self._cap_impact(impacts.get("gdp", 0)))
        self.employment = self._clamp(self.employment + self._cap_impact(impacts.get("employment", 0)))
        self.inflation = self._clamp(self.inflation + self._cap_impact(impacts.get("inflation", 0)))
        self.public_trust = self._clamp(self.public_trust + self._cap_impact(impacts.get("public_trust", 0)))
        self.trade_balance = self._clamp(self.trade_balance + self._cap_impact(impacts.get("trade_balance", 0)))
        self.national_debt = self._clamp(self.national_debt + self._cap_impact(impacts.get("national_debt", 0)))

    @staticmethod
    def _cap_impact(value: int) -> int:
        """
        Cap a single impact value to the range [-15, +15].

        This prevents any single policy from making extreme changes to an
        indicator in one round. For example, a policy that tries to set
        GDP impact to -50 will be capped to -15.

        Args:
            value: The raw impact value from the AI evaluation

        Returns:
            int: The capped value, guaranteed to be between -15 and +15
        """
        return max(-15, min(15, int(value)))

    def add_score_points(self, points: int):
        """
        Add points to the cumulative economy score.

        The AI assigns "destruction_points" (can be positive or negative)
        to each winning proposal. These accumulate across rounds and are
        displayed as the economy's total score at game over.

        Args:
            points: Points to add (positive = helped economy, negative = hurt it)
        """
        self.score += points

    def get_state(self) -> dict:
        """
        Return the current economy state as a dictionary.

        This is used frequently to:
        - Display the economy dashboard on the host screen
        - Send economy data to the LLM for context in generating scenarios
        - Record economy snapshots before/after each round in history

        Returns:
            dict: All 6 indicator values as key-value pairs
        """
        return {
            "gdp": self.gdp,
            "employment": self.employment,
            "inflation": self.inflation,
            "public_trust": self.public_trust,
            "trade_balance": self.trade_balance,
            "national_debt": self.national_debt,
        }

    def get_score(self) -> int:
        """
        Return the cumulative economy score across all rounds.

        Returns:
            int: Total accumulated destruction/prosperity points
        """
        return self.score

    def is_collapsed(self) -> bool:
        """
        Check if the economy has collapsed.

        The economy is considered collapsed if:
        - GDP drops to 0 (no economic output at all), OR
        - Employment drops to 0 (nobody has a job), OR
        - Both GDP and Employment are below 10 (near-total collapse)

        In destructive mode, a collapsed economy triggers an early game over
        (the players "won" by destroying the economy before all rounds finished).

        Returns:
            bool: True if the economy has collapsed
        """
        return self.gdp <= 0 or self.employment <= 0 or (self.gdp < 10 and self.employment < 10)

    @staticmethod
    def _clamp(value: int) -> int:
        """
        Clamp a value to the valid indicator range [0, 100].

        This ensures no indicator can go below 0 or above 100,
        regardless of how extreme the policy impacts are.

        Args:
            value: The raw value after applying impacts

        Returns:
            int: The clamped value, guaranteed to be between 0 and 100
        """
        return max(0, min(100, int(value)))
