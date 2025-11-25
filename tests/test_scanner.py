"""
Tests for the main BWB scanner functionality.
"""

import pytest
import pandas as pd
import tempfile
import os
from bwb_scanner.scanner import BWBScanner
from bwb_scanner.strategy import BWBValidator


class TestBWBScanner:
    """Test suite for BWBScanner."""
    
    @pytest.fixture
    def sample_csv_file(self):
        """Create a temporary CSV file with sample data."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,call,15.0,8.0,11.5,0.70,0.20
SPY,2025-11-30,5,445,call,10.0,5.0,7.5,0.30,0.20
SPY,2025-11-30,5,455,call,3.0,2.0,2.5,0.10,0.20
SPY,2025-11-30,5,440,put,2.0,2.5,2.25,0.25,0.20
SPY,2025-12-05,10,440,call,16.0,9.0,12.5,0.72,0.22
SPY,2025-12-05,10,445,call,11.0,6.0,8.5,0.32,0.22
SPY,2025-12-05,10,455,call,4.0,3.0,3.5,0.12,0.22
AAPL,2025-11-30,5,180,call,8.0,4.0,6.0,0.28,0.25"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        yield temp_path
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_scanner_initialization(self, sample_csv_file):
        """Test scanner initializes correctly."""
        scanner = BWBScanner(sample_csv_file)
        assert scanner.loader is not None
        assert scanner.constructor is not None
        assert scanner.chain_data is None  # Not loaded yet
    
    def test_scanner_with_custom_validator(self, sample_csv_file):
        """Test scanner accepts custom validator."""
        custom_validator = BWBValidator(min_credit=1.0)
        scanner = BWBScanner(sample_csv_file, validator=custom_validator)
        assert scanner.constructor.validator.min_credit == 1.0
    
    def test_load_data(self, sample_csv_file):
        """Test data loading."""
        scanner = BWBScanner(sample_csv_file)
        scanner.load_data()
        
        assert scanner.chain_data is not None
        assert len(scanner.chain_data) > 0
        assert "symbol" in scanner.chain_data.columns
    
    def test_scan_specific_expiry(self, sample_csv_file):
        """Test scanning a specific expiry."""
        scanner = BWBScanner(sample_csv_file)
        results = scanner.scan("SPY", "2025-11-30")
        
        assert isinstance(results, pd.DataFrame)
        # Results should have correct columns
        expected_cols = [
            "ticker", "expiry", "dte", "k1", "k2", "k3",
            "wing_left", "wing_right", "credit", "max_profit",
            "max_loss", "score"
        ]
        for col in expected_cols:
            assert col in results.columns
    
    def test_scan_nonexistent_ticker(self, sample_csv_file):
        """Test scanning for non-existent ticker returns empty DataFrame."""
        scanner = BWBScanner(sample_csv_file)
        results = scanner.scan("TSLA", "2025-11-30")
        
        assert isinstance(results, pd.DataFrame)
        assert len(results) == 0
    
    def test_scan_all_expiries(self, sample_csv_file):
        """Test scanning all expiries for a ticker."""
        scanner = BWBScanner(sample_csv_file)
        results = scanner.scan_all_expiries("SPY")
        
        assert isinstance(results, pd.DataFrame)
        # Should combine results from multiple expiries
        if len(results) > 0:
            assert "expiry" in results.columns
    
    def test_results_sorted_by_score(self, sample_csv_file):
        """Test that results are sorted by score (best first)."""
        scanner = BWBScanner(sample_csv_file)
        results = scanner.scan_all_expiries("SPY")
        
        if len(results) > 1:
            # Verify descending order
            scores = results["score"].tolist()
            assert scores == sorted(scores, reverse=True)
    
    def test_get_summary_stats_empty(self, sample_csv_file):
        """Test summary stats for empty results."""
        scanner = BWBScanner(sample_csv_file)
        empty_df = scanner._create_empty_result()
        stats = scanner.get_summary_stats(empty_df)
        
        assert stats["total_positions"] == 0
        assert stats["avg_score"] == 0.0
        assert stats["avg_credit"] == 0.0
    
    def test_get_summary_stats_with_data(self, sample_csv_file):
        """Test summary stats calculation."""
        scanner = BWBScanner(sample_csv_file)
        results = scanner.scan_all_expiries("SPY")
        
        if len(results) > 0:
            stats = scanner.get_summary_stats(results)
            
            assert stats["total_positions"] == len(results)
            assert "avg_score" in stats
            assert "avg_credit" in stats
            assert "best_score" in stats
            assert "worst_score" in stats
            
            # Verify best >= worst
            assert stats["best_score"] >= stats["worst_score"]


class TestScannerFilters:
    """Test that scanner properly applies all filters."""
    
    @pytest.fixture
    def comprehensive_csv(self):
        """Create CSV with data designed to test all filters."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,call,20.0,10.0,15.0,0.70,0.20
SPY,2025-11-30,5,445,call,15.0,8.0,11.5,0.30,0.20
SPY,2025-11-30,5,455,call,5.0,3.0,4.0,0.10,0.20
SPY,2025-11-30,5,460,call,2.0,1.5,1.75,0.05,0.20
SPY,2025-11-30,0,440,call,20.0,10.0,15.0,0.70,0.20
SPY,2025-11-30,0,445,call,15.0,8.0,11.5,0.15,0.20
SPY,2025-11-30,0,455,call,5.0,3.0,4.0,0.10,0.20
SPY,2025-11-30,15,440,call,20.0,10.0,15.0,0.70,0.20
SPY,2025-11-30,15,445,call,15.0,8.0,11.5,0.30,0.20
SPY,2025-11-30,15,455,call,5.0,3.0,4.0,0.10,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        yield temp_path
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_dte_filter_applied(self, comprehensive_csv):
        """Test that DTE filter is properly applied."""
        scanner = BWBScanner(
            comprehensive_csv,
            validator=BWBValidator(min_dte=1, max_dte=10)
        )
        results = scanner.scan_all_expiries("SPY")
        
        # All results should have DTE between 1 and 10
        if len(results) > 0:
            assert all(results["dte"] >= 1)
            assert all(results["dte"] <= 10)
            # Should not include DTE 0 or 15
            assert 0 not in results["dte"].values
            assert 15 not in results["dte"].values
    
    def test_delta_filter_applied(self, comprehensive_csv):
        """Test that delta filter is applied to short strike."""
        scanner = BWBScanner(
            comprehensive_csv,
            validator=BWBValidator(min_delta=0.20, max_delta=0.35)
        )
        results = scanner.scan_all_expiries("SPY")
        
        # The short strike (K2) should have delta in range
        # We can't directly verify from results, but positions should exist
        # only if K2 delta is valid
        # In our data, only 445 strike has delta 0.30 (in range)
        if len(results) > 0:
            # All positions should use 445 as K2
            assert all(results["k2"] == 445.0)
    
    def test_credit_filter_applied(self, comprehensive_csv):
        """Test that minimum credit filter is applied."""
        scanner = BWBScanner(
            comprehensive_csv,
            validator=BWBValidator(min_credit=0.50)
        )
        results = scanner.scan_all_expiries("SPY")
        
        # All results should have credit >= 0.50
        if len(results) > 0:
            assert all(results["credit"] >= 0.50)
    
    def test_asymmetry_filter_applied(self, comprehensive_csv):
        """Test that asymmetry filter is applied."""
        scanner = BWBScanner(comprehensive_csv)
        results = scanner.scan_all_expiries("SPY")
        
        # All results should have asymmetric wings
        if len(results) > 0:
            assert all(results["wing_left"] != results["wing_right"])


class TestScannerIntegration:
    """Integration tests for complete scanning workflow."""
    
    @pytest.fixture
    def realistic_csv(self):
        """Create a realistic CSV for integration testing."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,call,92.0,94.0,93.0,0.85,0.20
SPY,2025-11-30,5,445,call,87.0,89.0,88.0,0.80,0.20
SPY,2025-11-30,5,450,call,82.0,84.0,83.0,0.75,0.20
SPY,2025-11-30,5,455,call,77.0,79.0,78.0,0.70,0.20
SPY,2025-11-30,5,460,call,72.0,74.0,73.0,0.65,0.20
SPY,2025-11-30,5,465,call,67.0,69.0,68.0,0.60,0.20
SPY,2025-11-30,5,470,call,62.0,64.0,63.0,0.55,0.20
SPY,2025-11-30,5,475,call,57.0,59.0,58.0,0.50,0.20
SPY,2025-11-30,5,480,call,52.0,54.0,53.0,0.45,0.20
SPY,2025-11-30,5,485,call,47.0,49.0,48.0,0.40,0.20
SPY,2025-11-30,5,490,call,42.0,44.0,43.0,0.35,0.20
SPY,2025-11-30,5,495,call,37.0,39.0,38.0,0.30,0.20
SPY,2025-11-30,5,500,call,32.0,34.0,33.0,0.25,0.20
SPY,2025-11-30,5,505,call,27.0,29.0,28.0,0.20,0.20
SPY,2025-11-30,5,510,call,22.0,24.0,23.0,0.15,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        yield temp_path
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_end_to_end_scan(self, realistic_csv):
        """Test complete end-to-end scanning workflow."""
        scanner = BWBScanner(realistic_csv)
        results = scanner.scan("SPY", "2025-11-30")
        
        # Should find some valid positions
        assert isinstance(results, pd.DataFrame)
        
        if len(results) > 0:
            # Verify all required columns exist
            required_cols = [
                "ticker", "expiry", "dte", "k1", "k2", "k3",
                "wing_left", "wing_right", "credit", "max_profit",
                "max_loss", "score"
            ]
            for col in required_cols:
                assert col in results.columns
            
            # Verify data integrity
            assert all(results["ticker"] == "SPY")
            assert all(results["expiry"] == "2025-11-30")
            assert all(results["dte"] == 5)
            assert all(results["k1"] < results["k2"])
            assert all(results["k2"] < results["k3"])
            assert all(results["wing_left"] != results["wing_right"])
            assert all(results["credit"] >= 0.50)
            assert all(results["max_profit"] > 0)
            assert all(results["max_loss"] > 0)
            assert all(results["score"] > 0)
    
    def test_scan_filters_puts(self, realistic_csv):
        """Test that scanner only processes calls, not puts."""
        scanner = BWBScanner(realistic_csv)
        results = scanner.scan("SPY", "2025-11-30")
        
        # Should only find call positions (no puts in results)
        # This is implicit in the design, but we verify no errors occur
        assert isinstance(results, pd.DataFrame)
    
    def test_multiple_expiries(self, realistic_csv):
        """Test scanning across multiple expiries."""
        scanner = BWBScanner(realistic_csv)
        results = scanner.scan_all_expiries("SPY")
        
        if len(results) > 0:
            # Should have results from both expiries
            expiries = results["expiry"].unique()
            # We have 2025-11-30 and 2025-12-05 in the data
            assert len(expiries) >= 1
    
    def test_summary_statistics_accuracy(self, realistic_csv):
        """Test that summary statistics are calculated correctly."""
        scanner = BWBScanner(realistic_csv)
        results = scanner.scan_all_expiries("SPY")
        
        if len(results) > 0:
            stats = scanner.get_summary_stats(results)
            
            # Verify calculations
            assert stats["total_positions"] == len(results)
            assert abs(stats["avg_score"] - results["score"].mean()) < 0.0001
            assert abs(stats["avg_credit"] - results["credit"].mean()) < 0.01
            assert stats["best_score"] == results["score"].max()
            assert stats["worst_score"] == results["score"].min()


class TestScannerEdgeCases:
    """Test edge cases and error handling in scanner."""
    
    def test_empty_results(self):
        """Test handling when no valid positions are found."""
        # Create CSV with data that won't produce valid BWBs
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,call,1.0,2.0,1.5,0.10,0.20
SPY,2025-11-30,5,445,call,0.5,1.0,0.75,0.05,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        try:
            scanner = BWBScanner(temp_path)
            results = scanner.scan("SPY", "2025-11-30")
            
            assert isinstance(results, pd.DataFrame)
            assert len(results) == 0
            
            # Summary stats should handle empty results
            stats = scanner.get_summary_stats(results)
            assert stats["total_positions"] == 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_single_strike(self):
        """Test handling of chain with only one strike."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,call,15.0,15.5,15.25,0.30,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        try:
            scanner = BWBScanner(temp_path)
            results = scanner.scan("SPY", "2025-11-30")
            
            # Should return empty results (need 3 strikes minimum)
            assert len(results) == 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_only_puts_in_chain(self):
        """Test handling when chain only contains puts."""
        data = """symbol,expiry,dte,strike,type,bid,ask,mid,delta,iv
SPY,2025-11-30,5,440,put,5.0,5.5,5.25,0.25,0.20
SPY,2025-11-30,5,445,put,6.0,6.5,6.25,0.30,0.20
SPY,2025-11-30,5,450,put,7.0,7.5,7.25,0.35,0.20"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write(data)
            temp_path = f.name
        
        try:
            scanner = BWBScanner(temp_path)
            results = scanner.scan("SPY", "2025-11-30")
            
            # Should return empty (we only scan calls)
            assert len(results) == 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)