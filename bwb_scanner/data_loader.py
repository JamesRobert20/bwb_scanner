"""
Options chain data loader module.
Handles reading and validating options chain data from CSV files.
"""

from typing import Optional
import pandas as pd
from pathlib import Path


class OptionsChainLoader:
    """Loads and validates options chain data from CSV files."""
    
    REQUIRED_COLUMNS = [
        "symbol", "expiry", "dte", "strike", "type", 
        "bid", "ask", "mid", "delta", "iv"
    ]
    
    def __init__(self, csv_path: str):
        """
        Initialize the loader with a CSV file path.
        
        Args:
            csv_path: Path to the options chain CSV file
        """
        self.csv_path = Path(csv_path)
        self._validate_file_exists()
    
    def _validate_file_exists(self) -> None:
        """Validate that the CSV file exists."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validate that all required columns are present.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            ValueError: If required columns are missing
        """
        missing_cols = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
    
    def _validate_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and convert data types.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            DataFrame with corrected types
        """
        df = df.copy()
        
        # Numeric columns
        numeric_cols = ["dte", "strike", "bid", "ask", "mid", "delta", "iv"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        
        # String columns
        df["symbol"] = df["symbol"].astype(str).str.upper()
        df["type"] = df["type"].astype(str).str.lower()
        df["expiry"] = df["expiry"].astype(str)
        
        # Validate option types
        valid_types = {"call", "put"}
        invalid_types = set(df["type"].unique()) - valid_types
        if invalid_types:
            raise ValueError(f"Invalid option types found: {invalid_types}")
        
        return df
    
    def _validate_market_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate market data integrity.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            DataFrame with invalid rows removed
        """
        initial_len = len(df)
        
        # Remove rows with negative prices
        df = df[(df["bid"] >= 0) & (df["ask"] >= 0) & (df["strike"] > 0)]
        
        # Remove rows where bid > ask (invalid market data)
        df = df[df["bid"] <= df["ask"]]
        
        # Remove rows with invalid DTE (must be >= 0)
        df = df[df["dte"] >= 0]
        
        # Remove rows with invalid delta for calls (0-1) and puts (-1 to 0)
        calls_valid = (df["type"] == "call") & (df["delta"] >= 0) & (df["delta"] <= 1)
        puts_valid = (df["type"] == "put") & (df["delta"] >= -1) & (df["delta"] <= 0)
        df = df[calls_valid | puts_valid]
        
        removed = initial_len - len(df)
        if removed > 0:
            import warnings
            warnings.warn(f"Removed {removed} rows with invalid market data")
        
        return df
    
    def load(self) -> pd.DataFrame:
        """
        Load and validate the options chain data.
        
        Returns:
            Validated DataFrame with options chain data
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If data validation fails
        """
        df = pd.read_csv(self.csv_path)
        self._validate_columns(df)
        df = self._validate_data_types(df)
        
        # Remove rows with missing critical data
        df = df.dropna(subset=["strike", "bid", "ask", "delta"])
        
        # Validate market data integrity
        df = self._validate_market_data(df)
        
        return df
    
    def filter_by_ticker_and_expiry(
        self, 
        df: pd.DataFrame, 
        ticker: str, 
        expiry: str
    ) -> pd.DataFrame:
        """
        Filter options chain by ticker and expiry.
        
        Args:
            df: Options chain DataFrame
            ticker: Ticker symbol to filter
            expiry: Expiry date to filter
            
        Returns:
            Filtered DataFrame
        """
        return df[
            (df["symbol"] == ticker.upper()) & 
            (df["expiry"] == expiry)
        ].copy()
    
    def filter_calls_only(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter to include only call options.
        
        Args:
            df: Options chain DataFrame
            
        Returns:
            DataFrame with only call options
        """
        return df[df["type"] == "call"].copy()