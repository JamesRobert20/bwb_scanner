"""
Generates realistic sample options chain data for testing.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List


class OptionsChainGenerator:
    """Generates realistic options chain data for testing."""
    
    def __init__(self, ticker: str = "SPY", seed: int = 42):
        """
        Initialize generator.
        
        Args:
            ticker: Ticker symbol
            seed: Random seed for reproducibility
        """
        self.ticker = ticker
        np.random.seed(seed)
    
    def _generate_strikes(
        self,
        spot_price: float,
        num_strikes: int = 30
    ) -> List[float]:
        """
        Generate strike prices around spot price.
        
        Args:
            spot_price: Current spot price
            num_strikes: Number of strikes to generate
            
        Returns:
            List of strike prices
        """
        # Generate strikes from 80% to 120% of spot
        min_strike = spot_price * 0.80
        max_strike = spot_price * 1.20
        
        # Round to nearest dollar for SPY-like strikes
        strikes = np.linspace(min_strike, max_strike, num_strikes)
        strikes = np.round(strikes).astype(int)
        
        return sorted(set(strikes))
    
    def _calculate_delta(
        self,
        strike: float,
        spot_price: float,
        option_type: str,
        dte: int
    ) -> float:
        """
        Calculate approximate delta using simplified model.
        
        Args:
            strike: Strike price
            spot_price: Current spot price
            option_type: "call" or "put"
            dte: Days to expiration
            
        Returns:
            Approximate delta value
        """
        # Simplified delta calculation
        moneyness = (spot_price - strike) / spot_price
        time_factor = np.sqrt(dte / 365.0)
        
        if option_type == "call":
            # Calls: delta increases as strike decreases
            base_delta = 0.5 + (moneyness * 2.0)
            delta = base_delta * (1 - 0.3 * time_factor)
        else:
            # Puts: delta decreases as strike increases
            base_delta = -0.5 + (moneyness * 2.0)
            delta = base_delta * (1 - 0.3 * time_factor)
        
        # Clamp delta to valid range
        if option_type == "call":
            delta = np.clip(delta, 0.01, 0.99)
        else:
            delta = np.clip(delta, -0.99, -0.01)
        
        return round(delta, 4)
    
    def _calculate_iv(
        self,
        strike: float,
        spot_price: float,
        dte: int,
        base_iv: float = 0.20
    ) -> float:
        """
        Calculate implied volatility with volatility smile.
        
        Args:
            strike: Strike price
            spot_price: Current spot price
            dte: Days to expiration
            base_iv: Base implied volatility
            
        Returns:
            Implied volatility
        """
        moneyness = abs(strike - spot_price) / spot_price
        smile_factor = 1.0 + (moneyness * 0.5)
        
        term_factor = 1.0 + 0.05 / max(1, np.sqrt(dte / 30))
        
        iv = base_iv * smile_factor * term_factor
        
        noise = np.random.normal(0, 0.01)
        iv = iv + noise
        
        return round(max(0.05, min(1.5, iv)), 4)
    
    def _calculate_option_price(
        self,
        strike: float,
        spot_price: float,
        option_type: str,
        dte: int,
        iv: float
    ) -> tuple:
        """
        Calculate approximate option bid/ask prices.
        
        Args:
            strike: Strike price
            spot_price: Current spot price
            option_type: "call" or "put"
            dte: Days to expiration
            iv: Implied volatility
            
        Returns:
            Tuple of (bid, ask, mid)
        """
        # Simplified Black-Scholes approximation
        intrinsic = max(0, spot_price - strike) if option_type == "call" else max(0, strike - spot_price)
        
        # Time value based on IV and DTE
        time_value = iv * spot_price * np.sqrt(dte / 365.0) * 0.4
        
        # Adjust time value based on moneyness
        moneyness = abs(strike - spot_price) / spot_price
        if moneyness > 0.1:  # OTM
            time_value *= (1 - moneyness)
        
        mid_price = intrinsic + time_value
        
        # Add bid-ask spread (wider for lower prices)
        spread_pct = 0.02 if mid_price > 1.0 else 0.05
        spread = max(0.01, mid_price * spread_pct)
        
        bid = max(0.01, mid_price - spread / 2)
        ask = mid_price + spread / 2
        
        return round(bid, 2), round(ask, 2), round(mid_price, 2)
    
    def generate_chain(
        self,
        spot_price: float = 450.0,
        dte_list: List[int] = None,
        num_strikes: int = 30
    ) -> pd.DataFrame:
        """
        Generate complete options chain.
        
        Args:
            spot_price: Current spot price
            dte_list: List of DTEs to generate (default: [3, 5, 7, 10])
            num_strikes: Number of strikes per expiry
            
        Returns:
            DataFrame with options chain data
        """
        if dte_list is None:
            dte_list = [3, 5, 7, 10]
        
        strikes = self._generate_strikes(spot_price, num_strikes)
        
        rows = []
        base_date = datetime.now()
        
        for dte in dte_list:
            expiry_date = (base_date + timedelta(days=dte)).strftime("%Y-%m-%d")
            
            for strike in strikes:
                for option_type in ["call", "put"]:
                    delta = self._calculate_delta(strike, spot_price, option_type, dte)
                    iv = self._calculate_iv(strike, spot_price, dte)
                    bid, ask, mid = self._calculate_option_price(
                        strike, spot_price, option_type, dte, iv
                    )
                    
                    rows.append({
                        "symbol": self.ticker,
                        "expiry": expiry_date,
                        "dte": dte,
                        "strike": strike,
                        "type": option_type,
                        "bid": bid,
                        "ask": ask,
                        "mid": mid,
                        "delta": delta,
                        "iv": iv
                    })
        
        df = pd.DataFrame(rows)
        return df
    
    def save_to_csv(self, df: pd.DataFrame, filename: str) -> None:
        """
        Save options chain to CSV file.
        
        Args:
            df: Options chain DataFrame
            filename: Output filename
        """
        df.to_csv(filename, index=False)