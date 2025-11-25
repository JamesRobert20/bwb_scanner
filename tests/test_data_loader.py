"""
Tests for data loading and validation.
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import os
from bwb_scanner.data_loader import OptionsChainLoader


class TestOptionsChainLoader:
    """Test suite for OptionsChainLoader."""
    
    @pytest.fixture
    def valid_csv_file(self):
        """Create a temporary valid CSV file for testing."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,call,15.0,15.5,15.25,0.70,0.20
SPY,2025-11-30,5,445,call,10.0,10.5,10.25,0.30,0.20
SPY,2025-11-30,5,450,put,5.0,5.5,5.25,-0.25,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    @pytest.fixture
    def invalid_columns_csv(self):
        """Create a CSV with missing required columns."""
        data = """symbol,expiry,strike,type
SPY,2025-11-30,440,call"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        yield temp_path
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_initialization_valid_file(self, valid_csv_file):
        """Test loader initializes with valid file."""
        loader = OptionsChainLoader(valid_csv_file)
        assert loader.csv_path == Path(valid_csv_file)
    
    def test_initialization_invalid_file(self):
        """Test loader raises error for non-existent file."""
        with pytest.raises(FileNotFoundError):
            OptionsChainLoader("nonexistent_file.csv")
    
    def test_load_valid_data(self, valid_csv_file):
        """Test loading valid CSV data."""
        loader = OptionsChainLoader(valid_csv_file)
        df = loader.load()
        
        assert len(df) == 3
        assert "symbol" in df.columns
        assert "strike" in df.columns
        assert df["symbol"].iloc[0] == "SPY"
    
    def test_load_missing_columns(self, invalid_columns_csv):
        """Test that missing columns raise ValueError."""
        loader = OptionsChainLoader(invalid_columns_csv)
        with pytest.raises(ValueError, match="Missing required columns"):
            loader.load()
    
    def test_validate_data_types(self, valid_csv_file):
        """Test data type validation and conversion."""
        loader = OptionsChainLoader(valid_csv_file)
        df = loader.load()
        
        # Check numeric columns
        assert pd.api.types.is_numeric_dtype(df["dte"])
        assert pd.api.types.is_numeric_dtype(df["strike"])
        assert pd.api.types.is_numeric_dtype(df["bid"])
        assert pd.api.types.is_numeric_dtype(df["delta"])
        
        # Check string columns
        assert df["symbol"].dtype == object
        assert df["type"].dtype == object
    
    def test_option_type_validation(self):
        """Test that invalid option types are rejected."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,invalid,15.0,15.5,15.25,0.70,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        try:
            loader = OptionsChainLoader(temp_path)
            with pytest.raises(ValueError, match="Invalid option types"):
                loader.load()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_filter_by_ticker_and_expiry(self, valid_csv_file):
        """Test filtering by ticker and expiry."""
        loader = OptionsChainLoader(valid_csv_file)
        df = loader.load()
        
        filtered = loader.filter_by_ticker_and_expiry(df, "SPY", "2025-11-30")
        assert len(filtered) == 3
        assert all(filtered["symbol"] == "SPY")
        assert all(filtered["expiry"] == "2025-11-30")
        
        # Test with non-existent ticker
        filtered = loader.filter_by_ticker_and_expiry(df, "AAPL", "2025-11-30")
        assert len(filtered) == 0
    
    def test_filter_calls_only(self, valid_csv_file):
        """Test filtering for call options only."""
        loader = OptionsChainLoader(valid_csv_file)
        df = loader.load()
        
        calls = loader.filter_calls_only(df)
        assert len(calls) == 2  # Only 2 calls in the sample data
        assert all(calls["type"] == "call")
    
    def test_case_insensitive_ticker(self):
        """Test that ticker filtering is case-insensitive."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
spy,2025-11-30,5,440,call,15.0,15.5,15.25,0.70,0.20
SPY,2025-11-30,5,445,call,10.0,10.5,10.25,0.30,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        try:
            loader = OptionsChainLoader(temp_path)
            df = loader.load()
            
            # Both should be converted to uppercase
            assert all(df["symbol"] == "SPY")
            
            # Filter should work with any case
            filtered = loader.filter_by_ticker_and_expiry(df, "spy", "2025-11-30")
            assert len(filtered) == 2
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_missing_data_handling(self):
        """Test that rows with missing critical data are removed."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,call,15.0,15.5,15.25,0.70,0.20
SPY,2025-11-30,5,445,call,,,10.25,0.30,0.20
SPY,2025-11-30,5,450,call,10.0,10.5,10.25,,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        try:
            loader = OptionsChainLoader(temp_path)
            df = loader.load()
            
            # Should only have 1 row (the valid one)
            assert len(df) == 1
            assert df["strike"].iloc[0] == 440.0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestDataIntegrity:
    """Test suite for data integrity checks."""
    
    def test_required_columns_present(self):
        """Test that all required columns are defined."""
        expected_columns = [
            "symbol", "expiry", "dte", "strike", "type",
            "bid", "ask", "mid", "delta", "iv"
        ]
        assert OptionsChainLoader.REQUIRED_COLUMNS == expected_columns
    
    def test_option_types_normalized(self):
        """Test that option types are normalized to lowercase."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,CALL,15.0,15.5,15.25,0.70,0.20
SPY,2025-11-30,5,445,Call,10.0,10.5,10.25,0.30,0.20
SPY,2025-11-30,5,450,put,5.0,5.5,5.25,-0.25,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        try:
            loader = OptionsChainLoader(temp_path)
            df = loader.load()
            
            # All types should be lowercase
            assert all(df["type"].isin(["call", "put"]))
            assert df["type"].iloc[0] == "call"
            assert df["type"].iloc[1] == "call"
            assert df["type"].iloc[2] == "put"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)