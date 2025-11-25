"""
Main BWB scanner module that orchestrates the scanning process.
"""

from typing import Optional
import pandas as pd
from .data_loader import OptionsChainLoader
from .strategy import BWBConstructor, BWBValidator


class BWBScanner:
    """
    Main scanner class that coordinates data loading, 
    BWB construction, and result generation.
    """
    
    def __init__(
        self,
        csv_path: str,
        validator: Optional[BWBValidator] = None
    ):
        """
        Initialize scanner with data source and validator.
        
        Args:
            csv_path: Path to options chain CSV file
            validator: Optional BWBValidator instance
        """
        self.loader = OptionsChainLoader(csv_path)
        self.constructor = BWBConstructor(validator)
        self.chain_data: Optional[pd.DataFrame] = None
    
    def load_data(self) -> None:
        """Load and validate options chain data."""
        self.chain_data = self.loader.load()
    
    def scan(
        self,
        ticker: str,
        expiry: str
    ) -> pd.DataFrame:
        """
        Scan for valid BWB positions for a given ticker and expiry.
        
        Args:
            ticker: Ticker symbol to scan
            expiry: Expiry date to scan
            
        Returns:
            DataFrame with valid BWB positions sorted by score (best first)
        """
        if self.chain_data is None:
            self.load_data()
        
        # Filter chain for ticker and expiry
        filtered_chain = self.loader.filter_by_ticker_and_expiry(
            self.chain_data,
            ticker,
            expiry
        )
        
        if filtered_chain.empty:
            return self._create_empty_result()
        
        # Filter for calls only
        calls_chain = self.loader.filter_calls_only(filtered_chain)
        
        if calls_chain.empty:
            return self._create_empty_result()
        
        # Find all valid BWB combinations
        positions = self.constructor.find_all_combinations(calls_chain)
        
        if not positions:
            return self._create_empty_result()
        
        # Convert to DataFrame
        results_df = pd.DataFrame([pos.to_dict() for pos in positions])
        
        # Sort by score (best first)
        results_df = results_df.sort_values("score", ascending=False)
        results_df = results_df.reset_index(drop=True)
        
        return results_df
    
    def scan_all_expiries(self, ticker: str) -> pd.DataFrame:
        """
        Scan for valid BWB positions across all expiries for a ticker.
        
        Args:
            ticker: Ticker symbol to scan
            
        Returns:
            DataFrame with all valid BWB positions sorted by score
        """
        if self.chain_data is None:
            self.load_data()
        
        # Get all expiries for this ticker
        ticker_data = self.chain_data[
            self.chain_data["symbol"] == ticker.upper()
        ]
        
        if ticker_data.empty:
            return self._create_empty_result()
        
        expiries = ticker_data["expiry"].unique()
        
        all_results = []
        for expiry in expiries:
            expiry_results = self.scan(ticker, expiry)
            if not expiry_results.empty:
                all_results.append(expiry_results)
        
        if not all_results:
            return self._create_empty_result()
        
        # Combine all results
        combined_df = pd.concat(all_results, ignore_index=True)
        combined_df = combined_df.sort_values("score", ascending=False)
        combined_df = combined_df.reset_index(drop=True)
        
        return combined_df
    
    def _create_empty_result(self) -> pd.DataFrame:
        """Create an empty DataFrame with correct columns."""
        return pd.DataFrame(columns=[
            "ticker", "expiry", "dte", "k1", "k2", "k3",
            "wing_left", "wing_right", "credit", "max_profit",
            "max_loss", "score"
        ])
    
    def get_summary_stats(self, results: pd.DataFrame) -> dict:
        """
        Generate summary statistics for scan results.
        
        Args:
            results: DataFrame with scan results
            
        Returns:
            Dictionary with summary statistics
        """
        if results.empty:
            return {
                "total_positions": 0,
                "avg_score": 0.0,
                "avg_credit": 0.0,
                "avg_max_profit": 0.0,
                "avg_max_loss": 0.0
            }
        
        return {
            "total_positions": len(results),
            "avg_score": round(results["score"].mean(), 4),
            "avg_credit": round(results["credit"].mean(), 2),
            "avg_max_profit": round(results["max_profit"].mean(), 2),
            "avg_max_loss": round(results["max_loss"].mean(), 2),
            "best_score": round(results["score"].max(), 4),
            "worst_score": round(results["score"].min(), 4)
        }