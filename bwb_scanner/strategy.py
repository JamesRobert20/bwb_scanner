"""
BWB (Broken Wing Butterfly) strategy validation and construction module.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import pandas as pd


@dataclass
class BWBPosition:
    """Represents a single BWB position with all strikes and metrics."""
    
    ticker: str
    expiry: str
    dte: int
    k1: float
    k2: float
    k3: float
    wing_left: float
    wing_right: float
    credit: float
    max_profit: float
    max_loss: float
    score: float
    
    def to_dict(self) -> Dict:
        """Convert position to dictionary for DataFrame creation."""
        return {
            "ticker": self.ticker,
            "expiry": self.expiry,
            "dte": self.dte,
            "k1": self.k1,
            "k2": self.k2,
            "k3": self.k3,
            "wing_left": self.wing_left,
            "wing_right": self.wing_right,
            "credit": self.credit,
            "max_profit": self.max_profit,
            "max_loss": self.max_loss,
            "score": self.score
        }


class BWBValidator:
    """Validates BWB strategy constraints."""
    
    def __init__(
        self,
        min_dte: int = 1,
        max_dte: int = 10,
        min_delta: float = 0.20,
        max_delta: float = 0.35,
        min_credit: float = 0.50
    ):
        """
        Initialize validator with strategy constraints.
        
        Args:
            min_dte: Minimum days to expiration
            max_dte: Maximum days to expiration
            min_delta: Minimum delta for short strike
            max_delta: Maximum delta for short strike
            min_credit: Minimum net credit required
        """
        self.min_dte = min_dte
        self.max_dte = max_dte
        self.min_delta = min_delta
        self.max_delta = max_delta
        self.min_credit = min_credit
    
    def is_valid_dte(self, dte: int) -> bool:
        """Check if DTE is within valid range."""
        return self.min_dte <= dte <= self.max_dte
    
    def is_valid_delta(self, delta: float) -> bool:
        """Check if delta is within valid range."""
        return self.min_delta <= delta <= self.max_delta
    
    def is_asymmetric(self, k1: float, k2: float, k3: float) -> bool:
        """Check if wings are asymmetric."""
        wing_left = k2 - k1
        wing_right = k3 - k2
        return wing_left != wing_right
    
    def is_valid_credit(self, credit: float) -> bool:
        """Check if credit meets minimum requirement."""
        return credit >= self.min_credit


class BWBCalculator:
    """Calculates BWB position metrics."""
    
    @staticmethod
    def calculate_credit(
        ask_k1: float,
        bid_k2: float,
        ask_k3: float
    ) -> float:
        """
        Calculate net credit received.
        
        Args:
            ask_k1: Ask price for long call at K1 (you pay ask when buying)
            bid_k2: Bid price for short calls at K2 (you receive bid when selling)
            ask_k3: Ask price for long call at K3 (you pay ask when buying)
            
        Returns:
            Net credit received (positive = credit, negative = debit)
        """
        return (2 * bid_k2) - ask_k1 - ask_k3
    
    @staticmethod
    def calculate_max_profit(credit: float) -> float:
        """
        Calculate maximum profit.
        
        Args:
            credit: Net credit received
            
        Returns:
            Maximum profit (credit * 100)
        """
        return credit * 100
    
    @staticmethod
    def calculate_max_loss(
        k1: float,
        k2: float,
        k3: float,
        max_profit: float
    ) -> float:
        """
        Calculate maximum loss.
        
        Args:
            k1: Strike price of long call 1
            k2: Strike price of short calls
            k3: Strike price of long call 2
            max_profit: Maximum profit
            
        Returns:
            Maximum loss
        """
        wing_left = k2 - k1
        wing_right = k3 - k2
        larger_wing = max(wing_left, wing_right)
        return (larger_wing * 100) - max_profit
    
    @staticmethod
    def calculate_score(max_profit: float, max_loss: float) -> float:
        if max_loss == 0:
            return 0.0
        raw_score = (max_profit / max_loss) * 100
        return min(raw_score, 100.0)


class BWBConstructor:
    """Constructs and validates BWB positions from options chain."""
    
    def __init__(self, validator: Optional[BWBValidator] = None):
        """
        Initialize constructor with validator.
        
        Args:
            validator: BWBValidator instance (creates default if None)
        """
        self.validator = validator or BWBValidator()
        self.calculator = BWBCalculator()
    
    def _get_strike_data(
        self,
        chain: pd.DataFrame,
        strike: float
    ) -> Optional[pd.Series]:
        """
        Get option data for a specific strike.
        
        Args:
            chain: Options chain DataFrame
            strike: Strike price to find
            
        Returns:
            Series with option data or None if not found
        """
        matches = chain[chain["strike"] == strike]
        if len(matches) == 0:
            return None
        return matches.iloc[0]
    
    def _build_position(
        self,
        chain: pd.DataFrame,
        k1: float,
        k2: float,
        k3: float
    ) -> Optional[BWBPosition]:
        """
        Build a BWB position from three strikes.
        
        Args:
            chain: Options chain DataFrame
            k1: Long call strike 1
            k2: Short call strike
            k3: Long call strike 2
            
        Returns:
            BWBPosition if valid, None otherwise
        """
        # Get option data for each strike
        opt_k1 = self._get_strike_data(chain, k1)
        opt_k2 = self._get_strike_data(chain, k2)
        opt_k3 = self._get_strike_data(chain, k3)
        
        if opt_k1 is None or opt_k2 is None or opt_k3 is None:
            return None
        
        # Validate DTE (should be same for all)
        dte = int(opt_k2["dte"])
        if not self.validator.is_valid_dte(dte):
            return None
        
        # Validate short strike delta
        if not self.validator.is_valid_delta(opt_k2["delta"]):
            return None
        
        # Validate asymmetry
        if not self.validator.is_asymmetric(k1, k2, k3):
            return None
        
        credit = self.calculator.calculate_credit(
            opt_k1["ask"],
            opt_k2["bid"],
            opt_k3["ask"]
        )
        
        # Validate credit
        if not self.validator.is_valid_credit(credit):
            return None
        
        max_profit = self.calculator.calculate_max_profit(credit)
        max_loss = self.calculator.calculate_max_loss(k1, k2, k3, max_profit)
        score = self.calculator.calculate_score(max_profit, max_loss)
        
        wing_left = k2 - k1
        wing_right = k3 - k2
        
        return BWBPosition(
            ticker=str(opt_k2["symbol"]),
            expiry=str(opt_k2["expiry"]),
            dte=dte,
            k1=k1,
            k2=k2,
            k3=k3,
            wing_left=wing_left,
            wing_right=wing_right,
            credit=round(credit, 2),
            max_profit=round(max_profit, 2),
            max_loss=round(max_loss, 2),
            score=round(score, 4)
        )
    
    def find_all_combinations(
        self,
        chain: pd.DataFrame
    ) -> List[BWBPosition]:
        """
        Find all valid BWB combinations in the options chain.
        
        Args:
            chain: Options chain DataFrame (calls only)
            
        Returns:
            List of valid BWBPosition objects
        """
        positions = []
        strikes = sorted(chain["strike"].unique())
        
        # Iterate through all possible combinations
        for i, k1 in enumerate(strikes):
            for j, k2 in enumerate(strikes[i+1:], start=i+1):
                for k3 in strikes[j+1:]:
                    position = self._build_position(chain, k1, k2, k3)
                    if position is not None:
                        positions.append(position)
        
        return positions