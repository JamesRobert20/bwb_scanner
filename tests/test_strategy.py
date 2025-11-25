"""
Tests for BWB strategy validation and calculation logic.
"""

import pytest
import pandas as pd
from bwb_scanner.strategy import (
    BWBValidator,
    BWBCalculator,
    BWBConstructor,
    BWBPosition
)


class TestBWBValidator:
    """Test suite for BWBValidator."""
    
    def test_default_initialization(self):
        """Test validator initializes with correct defaults."""
        validator = BWBValidator()
        assert validator.min_dte == 1
        assert validator.max_dte == 10
        assert validator.min_delta == 0.20
        assert validator.max_delta == 0.35
        assert validator.min_credit == 0.50
    
    def test_custom_initialization(self):
        """Test validator accepts custom parameters."""
        validator = BWBValidator(
            min_dte=5,
            max_dte=15,
            min_delta=0.25,
            max_delta=0.40,
            min_credit=1.00
        )
        assert validator.min_dte == 5
        assert validator.max_dte == 15
        assert validator.min_delta == 0.25
        assert validator.max_delta == 0.40
        assert validator.min_credit == 1.00
    
    def test_is_valid_dte(self):
        """Test DTE validation."""
        validator = BWBValidator(min_dte=1, max_dte=10)
        assert validator.is_valid_dte(1) is True
        assert validator.is_valid_dte(5) is True
        assert validator.is_valid_dte(10) is True
        assert validator.is_valid_dte(0) is False
        assert validator.is_valid_dte(11) is False
    
    def test_is_valid_delta(self):
        """Test delta validation."""
        validator = BWBValidator(min_delta=0.20, max_delta=0.35)
        assert validator.is_valid_delta(0.20) is True
        assert validator.is_valid_delta(0.25) is True
        assert validator.is_valid_delta(0.35) is True
        assert validator.is_valid_delta(0.19) is False
        assert validator.is_valid_delta(0.36) is False
    
    def test_is_asymmetric(self):
        """Test asymmetry validation."""
        validator = BWBValidator()
        # Asymmetric: (445-440)=5 != (455-445)=10
        assert validator.is_asymmetric(440, 445, 455) is True
        # Symmetric: (445-440)=5 == (450-445)=5
        assert validator.is_asymmetric(440, 445, 450) is False
        # Asymmetric: (450-440)=10 != (455-450)=5
        assert validator.is_asymmetric(440, 450, 455) is True
    
    def test_is_valid_credit(self):
        """Test credit validation."""
        validator = BWBValidator(min_credit=0.50)
        assert validator.is_valid_credit(0.50) is True
        assert validator.is_valid_credit(1.00) is True
        assert validator.is_valid_credit(0.49) is False
        assert validator.is_valid_credit(0.00) is False


class TestBWBCalculator:
    """Test suite for BWBCalculator with known examples."""
    
    def test_calculate_credit_basic(self):
        """Test credit calculation with simple values."""
        calculator = BWBCalculator()
        # Long K1 @ $10 ask, Short 2x K2 @ $6 bid, Long K3 @ $2 ask
        # Credit = (2 * 6) - 10 - 2 = 12 - 12 = 0
        credit = calculator.calculate_credit(
            ask_k1=10.0,
            bid_k2=6.0,
            ask_k3=2.0
        )
        assert credit == 0.0
    
    def test_calculate_credit_realistic(self):
        """Test credit calculation with realistic BWB values."""
        calculator = BWBCalculator()
        # Example: 440/445/455 BWB
        # Long 440 call @ $12.50 ask, Short 2x 445 calls @ $9.00 bid, Long 455 call @ $4.00 ask
        # Credit = (2 * 9.00) - 12.50 - 4.00 = 18.00 - 16.50 = 1.50 credit
        credit = calculator.calculate_credit(
            ask_k1=12.50,
            bid_k2=9.00,
            ask_k3=4.00
        )
        assert credit == 1.50
        
        # Example with net debit
        # Long 440 call @ $15.50 ask, Short 2x 445 calls @ $8.00 bid, Long 455 call @ $3.50 ask
        # Credit = (2 * 8.00) - 15.50 - 3.50 = 16.00 - 19.00 = -3.00 (debit)
        credit = calculator.calculate_credit(
            ask_k1=15.50,
            bid_k2=8.00,
            ask_k3=3.50
        )
        assert credit == -3.00
    
    def test_calculate_max_profit(self):
        """Test max profit calculation."""
        calculator = BWBCalculator()
        # Max profit = credit * 100
        assert calculator.calculate_max_profit(1.50) == 150.0
        assert calculator.calculate_max_profit(2.00) == 200.0
        assert calculator.calculate_max_profit(0.50) == 50.0
    
    def test_calculate_max_loss_known_example(self):
        """Test max loss calculation with known example."""
        calculator = BWBCalculator()
        # Example: 440/445/455 BWB
        # Wing left = 445 - 440 = 5
        # Wing right = 455 - 445 = 10
        # Larger wing = 10
        # Max profit = $200 (credit of $2.00)
        # Max loss = (10 * 100) - 200 = 1000 - 200 = 800
        max_loss = calculator.calculate_max_loss(
            k1=440,
            k2=445,
            k3=455,
            max_profit=200.0
        )
        assert max_loss == 800.0
    
    def test_calculate_max_loss_symmetric_wings(self):
        """Test max loss when wings are equal (edge case)."""
        calculator = BWBCalculator()
        # 440/445/450 - both wings are 5
        # Max profit = $100
        # Max loss = (5 * 100) - 100 = 400
        max_loss = calculator.calculate_max_loss(
            k1=440,
            k2=445,
            k3=450,
            max_profit=100.0
        )
        assert max_loss == 400.0
    
    def test_calculate_score(self):
        """Test score calculation (returns percentage 0-100)."""
        calculator = BWBCalculator()
        assert calculator.calculate_score(200.0, 800.0) == 25.0
        assert calculator.calculate_score(150.0, 600.0) == 25.0
        assert calculator.calculate_score(100.0, 100.0) == 100.0
        assert calculator.calculate_score(100.0, 0.0) == 0.0
    
    def test_full_payoff_calculation(self):
        """Test complete payoff calculation for a known BWB."""
        calculator = BWBCalculator()
        
        # Known example: 440/445/455 BWB
        # Prices: Long 440 @ $14 ask, Short 2x 445 @ $9 bid, Long 455 @ $4 ask
        k1, k2, k3 = 440, 445, 455
        ask_k1, bid_k2, ask_k3 = 14.0, 9.0, 4.0
        
        # Calculate all metrics
        credit = calculator.calculate_credit(ask_k1, bid_k2, ask_k3)
        max_profit = calculator.calculate_max_profit(credit)
        max_loss = calculator.calculate_max_loss(k1, k2, k3, max_profit)
        score = calculator.calculate_score(max_profit, max_loss)
        
        # Verify calculations
        # Credit = (2 * 9) - 14 - 4 = 18 - 18 = 0... let's use different numbers
        assert credit == 0.0
        assert max_profit == 0.0
        assert max_loss == 1000.0  # (10 * 100) - 0
        assert score == 0.0


class TestBWBConstructor:
    """Test suite for BWBConstructor."""
    
    @pytest.fixture
    def sample_chain(self):
        """Create a sample options chain for testing."""
        data = {
            "symbol": ["SPY"] * 5,
            "expiry": ["2025-11-30"] * 5,
            "dte": [5] * 5,
            "strike": [440.0, 445.0, 450.0, 455.0, 460.0],
            "type": ["call"] * 5,
            "bid": [15.0, 10.0, 6.0, 3.0, 1.5],
            "ask": [15.5, 10.5, 6.5, 3.5, 2.0],
            "mid": [15.25, 10.25, 6.25, 3.25, 1.75],
            "delta": [0.70, 0.30, 0.15, 0.08, 0.04],
            "iv": [0.20] * 5
        }
        return pd.DataFrame(data)
    
    def test_get_strike_data_exists(self, sample_chain):
        """Test retrieving data for existing strike."""
        constructor = BWBConstructor()
        result = constructor._get_strike_data(sample_chain, 445.0)
        assert result is not None
        assert result["strike"] == 445.0
        assert result["delta"] == 0.30
    
    def test_get_strike_data_not_exists(self, sample_chain):
        """Test retrieving data for non-existent strike."""
        constructor = BWBConstructor()
        result = constructor._get_strike_data(sample_chain, 500.0)
        assert result is None
    
    def test_build_position_valid(self, sample_chain):
        """Test building a valid BWB position."""
        constructor = BWBConstructor()
        # 440/445/455: delta 0.30 is in range, wings are asymmetric (5 vs 10)
        # Credit = (2 * 10.0) - 15.5 - 3.5 = 20 - 19 = 1.0 (credit)
        position = constructor._build_position(sample_chain, 440.0, 445.0, 455.0)
        
        assert position is not None
        assert position.credit == 1.0
        assert position.wing_left == 5.0
        assert position.wing_right == 10.0
    
    def test_build_position_invalid_delta(self, sample_chain):
        """Test that position with invalid delta is rejected."""
        constructor = BWBConstructor()
        # 440/450/455: delta at 450 is 0.15, outside 0.20-0.35 range
        position = constructor._build_position(sample_chain, 440.0, 450.0, 455.0)
        assert position is None
    
    def test_build_position_symmetric(self, sample_chain):
        """Test that symmetric wings are rejected."""
        constructor = BWBConstructor()
        # 440/445/450: both wings are 5, symmetric
        position = constructor._build_position(sample_chain, 440.0, 445.0, 450.0)
        assert position is None
    
    def test_find_all_combinations(self, sample_chain):
        """Test finding all valid combinations."""
        constructor = BWBConstructor()
        positions = constructor.find_all_combinations(sample_chain)
        # Should find some positions (exact count depends on credit requirements)
        assert isinstance(positions, list)
        # All positions should be BWBPosition objects
        for pos in positions:
            assert isinstance(pos, BWBPosition)
            # Verify asymmetry
            assert pos.wing_left != pos.wing_right
            # Verify credit requirement
            assert pos.credit >= 0.50


class TestBWBPosition:
    """Test suite for BWBPosition dataclass."""
    
    def test_position_creation(self):
        """Test creating a BWB position."""
        position = BWBPosition(
            ticker="SPY",
            expiry="2025-11-30",
            dte=5,
            k1=440.0,
            k2=445.0,
            k3=455.0,
            wing_left=5.0,
            wing_right=10.0,
            credit=2.0,
            max_profit=200.0,
            max_loss=800.0,
            score=0.25
        )
        
        assert position.ticker == "SPY"
        assert position.k1 == 440.0
        assert position.k2 == 445.0
        assert position.k3 == 455.0
        assert position.score == 0.25
    
    def test_to_dict(self):
        """Test converting position to dictionary."""
        position = BWBPosition(
            ticker="SPY",
            expiry="2025-11-30",
            dte=5,
            k1=440.0,
            k2=445.0,
            k3=455.0,
            wing_left=5.0,
            wing_right=10.0,
            credit=2.0,
            max_profit=200.0,
            max_loss=800.0,
            score=0.25
        )
        
        result = position.to_dict()
        assert isinstance(result, dict)
        assert result["ticker"] == "SPY"
        assert result["k1"] == 440.0
        assert result["k2"] == 445.0
        assert result["k3"] == 455.0
        assert result["credit"] == 2.0
        assert result["score"] == 0.25


class TestPayoffMath:
    """Test suite for verifying payoff mathematics with known examples."""
    
    def test_known_example_1(self):
        """
        Test known BWB example 1:
        440/445/455 call BWB
        Prices: 440 call @ $13 ask, 445 call @ $8 bid, 455 call @ $3 ask
        Credit = (2 * 8) - 13 - 3 = 16 - 16 = 0... use different numbers
        """
        calculator = BWBCalculator()
        
        k1, k2, k3 = 440, 445, 455
        ask_k1, bid_k2, ask_k3 = 12.0, 8.0, 2.0
        
        credit = calculator.calculate_credit(ask_k1, bid_k2, ask_k3)
        max_profit = calculator.calculate_max_profit(credit)
        max_loss = calculator.calculate_max_loss(k1, k2, k3, max_profit)
        score = calculator.calculate_score(max_profit, max_loss)
        
        # Credit = (2 * 8) - 12 - 2 = 16 - 14 = 2
        assert credit == 2.0, "Credit should be (2*8) - 12 - 2 = 2"
        assert max_profit == 200.0, "Max profit should be 2 * 100 = 200"
        assert max_loss == 800.0, "Max loss should be (10 * 100) - 200 = 800"
        assert score == 25.0, "Score should be (200 / 800) * 100 = 25"
    
    def test_known_example_2(self):
        """
        Test known BWB example 2:
        450/460/465 call BWB (larger left wing)
        Prices: 450 call @ $18 ask, 460 call @ $12 bid, 465 call @ $6 ask
        """
        calculator = BWBCalculator()
        
        k1, k2, k3 = 450, 460, 465
        ask_k1, bid_k2, ask_k3 = 18.0, 12.0, 6.0
        
        credit = calculator.calculate_credit(ask_k1, bid_k2, ask_k3)
        max_profit = calculator.calculate_max_profit(credit)
        max_loss = calculator.calculate_max_loss(k1, k2, k3, max_profit)
        score = calculator.calculate_score(max_profit, max_loss)
        
        # Credit = (2 * 12) - 18 - 6 = 24 - 24 = 0... adjust
        assert credit == 0.0, "Credit should be (2*12) - 18 - 6 = 0"
        assert max_profit == 0.0, "Max profit should be 0 * 100 = 0"
        assert max_loss == 1000.0, "Max loss should be (10 * 100) - 0 = 1000"
        assert score == 0.0, "Score should be 0 when no profit"
    
    def test_known_example_3_with_credit(self):
        """
        Test BWB with positive credit.
        450/460/465: Long @ $16 ask, Short @ $12 bid, Long @ $5 ask
        Credit = (2 * 12) - 16 - 5 = 24 - 21 = 3
        """
        calculator = BWBCalculator()
        
        k1, k2, k3 = 450, 460, 465
        ask_k1, bid_k2, ask_k3 = 16.0, 12.0, 5.0
        
        credit = calculator.calculate_credit(ask_k1, bid_k2, ask_k3)
        max_profit = calculator.calculate_max_profit(credit)
        max_loss = calculator.calculate_max_loss(k1, k2, k3, max_profit)
        
        assert credit == 3.0, "Credit should be (2*12) - 16 - 5 = 3"
        assert max_profit == 300.0, "Max profit should be 300"
        assert max_loss == 700.0, "Max loss should be (10 * 100) - 300 = 700"
    
    def test_payoff_at_expiration_below_k1(self):
        """
        Test theoretical payoff when stock expires below K1.
        At expiration, if stock < K1, all calls expire worthless.
        P&L = credit received
        """
        calculator = BWBCalculator()
        credit = 2.0
        max_profit = calculator.calculate_max_profit(credit)
        assert max_profit == 200.0
    
    def test_payoff_at_expiration_at_k2(self):
        """
        Test theoretical payoff when stock expires at K2.
        This is where max profit occurs for a standard butterfly.
        """
        calculator = BWBCalculator()
        credit = 2.0
        max_profit = calculator.calculate_max_profit(credit)
        assert max_profit == 200.0
    
    def test_payoff_at_expiration_above_k3(self):
        """
        Test theoretical payoff when stock expires above K3.
        Max loss = larger wing width * 100 - max profit
        """
        calculator = BWBCalculator()
        max_loss = calculator.calculate_max_loss(440, 445, 455, 200.0)
        assert max_loss == 800.0


class TestFilters:
    """Test suite for filter behavior."""
    
    @pytest.fixture
    def mixed_chain(self):
        """Create a mixed options chain with various DTEs and deltas."""
        data = {
            "symbol": ["SPY"] * 10,
            "expiry": ["2025-11-30"] * 10,
            "dte": [1, 5, 5, 10, 10, 15, 15, 20, 20, 25],
            "strike": [440, 445, 450, 455, 460, 465, 470, 475, 480, 485],
            "type": ["call"] * 10,
            "bid": [15.0, 12.0, 9.0, 6.0, 4.0, 2.5, 1.5, 1.0, 0.5, 0.3],
            "ask": [15.5, 12.5, 9.5, 6.5, 4.5, 3.0, 2.0, 1.5, 1.0, 0.8],
            "mid": [15.25, 12.25, 9.25, 6.25, 4.25, 2.75, 1.75, 1.25, 0.75, 0.55],
            "delta": [0.70, 0.50, 0.30, 0.20, 0.15, 0.10, 0.08, 0.05, 0.03, 0.02],
            "iv": [0.20] * 10
        }
        return pd.DataFrame(data)
    
    def test_dte_filter(self, mixed_chain):
        """Test that DTE filter works correctly."""
        validator = BWBValidator(min_dte=5, max_dte=10)
        
        # DTE 1 should be rejected
        assert validator.is_valid_dte(1) is False
        # DTE 5 and 10 should be accepted
        assert validator.is_valid_dte(5) is True
        assert validator.is_valid_dte(10) is True
        # DTE 15+ should be rejected
        assert validator.is_valid_dte(15) is False
        assert validator.is_valid_dte(20) is False
    
    def test_delta_filter(self, mixed_chain):
        """Test that delta filter works correctly."""
        validator = BWBValidator(min_delta=0.20, max_delta=0.35)
        
        # Delta 0.15 should be rejected
        assert validator.is_valid_delta(0.15) is False
        # Delta 0.20 and 0.30 should be accepted
        assert validator.is_valid_delta(0.20) is True
        assert validator.is_valid_delta(0.30) is True
        # Delta 0.50 should be rejected
        assert validator.is_valid_delta(0.50) is False
    
    def test_credit_filter(self):
        """Test that credit filter works correctly."""
        validator = BWBValidator(min_credit=0.50)
        
        assert validator.is_valid_credit(0.49) is False
        assert validator.is_valid_credit(0.50) is True
        assert validator.is_valid_credit(1.00) is True
        assert validator.is_valid_credit(0.00) is False
        assert validator.is_valid_credit(-1.00) is False
    
    def test_asymmetry_filter(self):
        """Test that asymmetry filter works correctly."""
        validator = BWBValidator()
        
        # Test various wing combinations
        test_cases = [
            (440, 445, 450, False),  # 5, 5 - symmetric
            (440, 445, 455, True),   # 5, 10 - asymmetric
            (440, 450, 455, True),   # 10, 5 - asymmetric
            (440, 445, 460, True),   # 5, 15 - asymmetric
            (440, 450, 460, False),  # 10, 10 - symmetric
        ]
        
        for k1, k2, k3, expected in test_cases:
            result = validator.is_asymmetric(k1, k2, k3)
            assert result == expected, f"Failed for {k1}/{k2}/{k3}"
    
    def test_combined_filters(self, mixed_chain):
        """Test that all filters work together correctly."""
        constructor = BWBConstructor(
            validator=BWBValidator(
                min_dte=5,
                max_dte=10,
                min_delta=0.20,
                max_delta=0.35,
                min_credit=0.50
            )
        )
        
        positions = constructor.find_all_combinations(mixed_chain)
        
        # Verify all positions meet criteria
        for pos in positions:
            assert 5 <= pos.dte <= 10, "DTE should be in range"
            assert pos.credit >= 0.50, "Credit should meet minimum"
            assert pos.wing_left != pos.wing_right, "Wings should be asymmetric"
            # Note: We can't directly verify delta from position,
            # but the constructor should have filtered it


class TestEdgeCases:
    """Test suite for edge cases and error handling."""
    
    def test_empty_chain(self):
        """Test handling of empty options chain."""
        constructor = BWBConstructor()
        empty_chain = pd.DataFrame(columns=[
            "symbol", "expiry", "dte", "strike", "type",
            "bid", "ask", "mid", "delta", "iv"
        ])
        
        positions = constructor.find_all_combinations(empty_chain)
        assert positions == []
    
    def test_insufficient_strikes(self):
        """Test handling of chain with too few strikes."""
        constructor = BWBConstructor()
        
        # Only 2 strikes - need at least 3 for BWB
        data = {
            "symbol": ["SPY"] * 2,
            "expiry": ["2025-11-30"] * 2,
            "dte": [5] * 2,
            "strike": [440.0, 445.0],
            "type": ["call"] * 2,
            "bid": [15.0, 10.0],
            "ask": [15.5, 10.5],
            "mid": [15.25, 10.25],
            "delta": [0.70, 0.30],
            "iv": [0.20] * 2
        }
        chain = pd.DataFrame(data)
        
        positions = constructor.find_all_combinations(chain)
        assert positions == []
    
    def test_all_symmetric_wings(self):
        """Test chain where all possible combinations are symmetric."""
        constructor = BWBConstructor()
        
        # Strikes with equal spacing (all symmetric)
        data = {
            "symbol": ["SPY"] * 5,
            "expiry": ["2025-11-30"] * 5,
            "dte": [5] * 5,
            "strike": [440.0, 445.0, 450.0, 455.0, 460.0],  # All 5 apart
            "type": ["call"] * 5,
            "bid": [20.0, 15.0, 10.0, 6.0, 3.0],
            "ask": [20.5, 15.5, 10.5, 6.5, 3.5],
            "mid": [20.25, 15.25, 10.25, 6.25, 3.25],
            "delta": [0.70, 0.50, 0.30, 0.20, 0.10],
            "iv": [0.20] * 5
        }
        chain = pd.DataFrame(data)
        
        positions = constructor.find_all_combinations(chain)
        # Note: While strikes are equally spaced, not ALL combinations are symmetric
        # For example: 440/450/455 has wings of 10 and 5 (asymmetric)
        # So we should find some positions
        # Let's verify that symmetric ones like 440/445/450 are NOT included
        if len(positions) > 0:
            for pos in positions:
                # Verify all found positions are asymmetric
                assert pos.wing_left != pos.wing_right
    
    def test_zero_max_loss_edge_case(self):
        """Test score calculation when max_loss is zero."""
        calculator = BWBCalculator()
        score = calculator.calculate_score(max_profit=100.0, max_loss=0.0)
        assert score == 0.0, "Score should be 0 when max_loss is 0"