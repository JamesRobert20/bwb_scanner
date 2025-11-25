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
        credit = calculator.calculate_credit(
            ask_k1=10.0,
            bid_k2=6.0,
            ask_k3=2.0
        )
        assert credit == 0.0
    
    def test_calculate_credit_realistic(self):
        """Test credit calculation with realistic BWB values."""
        calculator = BWBCalculator()
        credit = calculator.calculate_credit(
            ask_k1=12.50,
            bid_k2=9.00,
            ask_k3=4.00
        )
        assert credit == 1.50
        
        credit = calculator.calculate_credit(
            ask_k1=15.50,
            bid_k2=8.00,
            ask_k3=3.50
        )
        assert credit == -3.00
    
    def test_calculate_max_profit(self):
        """Test max profit calculation."""
        calculator = BWBCalculator()
        # Max profit = (credit + wing_left) * 100
        # 440/445/455: wing_left = 5
        assert calculator.calculate_max_profit(credit=2.0, wing_left=5.0) == 700.0
        assert calculator.calculate_max_profit(credit=1.5, wing_left=5.0) == 650.0
        assert calculator.calculate_max_profit(credit=0.0, wing_left=5.0) == 500.0
    
    def test_calculate_max_loss_known_example(self):
        """Test max loss calculation with known example."""
        calculator = BWBCalculator()
        # 440/445/455 BWB with $2 credit
        # wing_left = 5, wing_right = 10
        # Max loss = (10 - 5 - 2) * 100 = 300
        max_loss = calculator.calculate_max_loss(
            wing_left=5.0,
            wing_right=10.0,
            credit=2.0
        )
        assert max_loss == 300.0
    
    def test_calculate_max_loss_symmetric_wings(self):
        """Test max loss when wings are equal (edge case)."""
        calculator = BWBCalculator()
        # 440/445/450: wing_left = 5, wing_right = 5, credit = 1
        # Max loss = (5 - 5 - 1) * 100 = -100 -> clamped to 0
        max_loss = calculator.calculate_max_loss(
            wing_left=5.0,
            wing_right=5.0,
            credit=1.0
        )
        assert max_loss == 0.0
    
    def test_calculate_max_loss_debit_position(self):
        """Test max loss for debit position (loss below K1)."""
        calculator = BWBCalculator()
        # Debit of $3: if stock expires below K1, lose the debit
        max_loss = calculator.calculate_max_loss(
            wing_left=5.0,
            wing_right=5.0,
            credit=-3.0
        )
        assert max_loss == 300.0
    
    def test_calculate_score(self):
        """Test score calculation."""
        calculator = BWBCalculator()
        assert calculator.calculate_score(700.0, 300.0) == pytest.approx(233.33, rel=0.01)
        assert calculator.calculate_score(150.0, 600.0) == 25.0
        assert calculator.calculate_score(100.0, 100.0) == 100.0
        assert calculator.calculate_score(100.0, 0.0) == 100.0  # No loss = max score
    
    def test_full_payoff_calculation(self):
        """Test complete payoff calculation for a known BWB."""
        calculator = BWBCalculator()
        
        # 440/445/455 BWB
        # Prices: Long 440 @ $12 ask, Short 2x 445 @ $8 bid, Long 455 @ $2 ask
        k1, k2, k3 = 440, 445, 455
        ask_k1, bid_k2, ask_k3 = 12.0, 8.0, 2.0
        wing_left = k2 - k1  # 5
        wing_right = k3 - k2  # 10
        
        credit = calculator.calculate_credit(ask_k1, bid_k2, ask_k3)
        max_profit = calculator.calculate_max_profit(credit, wing_left)
        max_loss = calculator.calculate_max_loss(wing_left, wing_right, credit)
        score = calculator.calculate_score(max_profit, max_loss)
        
        # Credit = (2 * 8) - 12 - 2 = 2
        assert credit == 2.0
        # Max profit at K2 = (2 + 5) * 100 = 700
        assert max_profit == 700.0
        # Max loss above K3 = (10 - 5 - 2) * 100 = 300
        assert max_loss == 300.0
        # Score = 700 / 300 * 100 = 233.33
        assert score == pytest.approx(233.33, rel=0.01)


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
            "bid": [14.5, 10.0, 6.0, 3.0, 1.5],
            "ask": [15.5, 10.5, 6.5, 3.5, 2.0],
            "mid": [15.0, 10.25, 6.25, 3.25, 1.75],
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
        # Max profit = (1.0 + 5.0) * 100 = 600
        assert position.max_profit == 600.0
        # Max loss = (10 - 5 - 1) * 100 = 400
        assert position.max_loss == 400.0
    
    def test_build_position_invalid_delta(self, sample_chain):
        """Test that position with invalid delta is rejected."""
        constructor = BWBConstructor()
        position = constructor._build_position(sample_chain, 440.0, 450.0, 455.0)
        assert position is None
    
    def test_build_position_symmetric(self, sample_chain):
        """Test that symmetric wings are rejected."""
        constructor = BWBConstructor()
        position = constructor._build_position(sample_chain, 440.0, 445.0, 450.0)
        assert position is None
    
    def test_find_all_combinations(self, sample_chain):
        """Test finding all valid combinations."""
        constructor = BWBConstructor()
        positions = constructor.find_all_combinations(sample_chain)
        assert isinstance(positions, list)
        for pos in positions:
            assert isinstance(pos, BWBPosition)
            assert abs(pos.wing_left - pos.wing_right) > 0.001
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
        """Test 440/445/455 call BWB with $2 credit."""
        calculator = BWBCalculator()
        
        k1, k2, k3 = 440, 445, 455
        wing_left = k2 - k1  # 5
        wing_right = k3 - k2  # 10
        ask_k1, bid_k2, ask_k3 = 12.0, 8.0, 2.0
        
        credit = calculator.calculate_credit(ask_k1, bid_k2, ask_k3)
        max_profit = calculator.calculate_max_profit(credit, wing_left)
        max_loss = calculator.calculate_max_loss(wing_left, wing_right, credit)
        score = calculator.calculate_score(max_profit, max_loss)
        
        assert credit == 2.0
        assert max_profit == 700.0  # (2 + 5) * 100
        assert max_loss == 300.0  # (10 - 5 - 2) * 100
        assert score == pytest.approx(233.33, rel=0.01)


class TestPayoffAtUnderlying:
    """Test payoff at various underlying prices to validate payoff shape."""
    
    @staticmethod
    def calculate_payoff_at_expiry(spot: float, k1: float, k2: float, k3: float, credit: float) -> float:
        """Calculate BWB P&L at expiration for a given spot price."""
        long_k1 = max(0, spot - k1)
        short_k2 = -2 * max(0, spot - k2)
        long_k3 = max(0, spot - k3)
        intrinsic = long_k1 + short_k2 + long_k3
        return (credit + intrinsic) * 100
    
    def test_payoff_below_k1(self):
        """Below K1: all calls expire worthless, P&L = credit."""
        k1, k2, k3, credit = 440, 445, 455, 2.0
        payoff = self.calculate_payoff_at_expiry(spot=430, k1=k1, k2=k2, k3=k3, credit=credit)
        assert payoff == 200.0  # Just the credit
    
    def test_payoff_at_k1(self):
        """At K1: long K1 is ATM, P&L = credit."""
        k1, k2, k3, credit = 440, 445, 455, 2.0
        payoff = self.calculate_payoff_at_expiry(spot=440, k1=k1, k2=k2, k3=k3, credit=credit)
        assert payoff == 200.0
    
    def test_payoff_at_k2(self):
        """At K2: max profit point."""
        k1, k2, k3, credit = 440, 445, 455, 2.0
        payoff = self.calculate_payoff_at_expiry(spot=445, k1=k1, k2=k2, k3=k3, credit=credit)
        assert payoff == 700.0  # credit + (k2 - k1) = 2 + 5 = 7 * 100
    
    def test_payoff_between_k2_and_k3(self):
        """Between K2 and K3: profit decreases linearly."""
        k1, k2, k3, credit = 440, 445, 455, 2.0
        payoff = self.calculate_payoff_at_expiry(spot=450, k1=k1, k2=k2, k3=k3, credit=credit)
        # At 450: long_k1 = 10, short_k2 = -10, long_k3 = 0
        # intrinsic = 10 - 10 + 0 = 0, P&L = (2 + 0) * 100 = 200
        assert payoff == 200.0
    
    def test_payoff_at_k3(self):
        """At K3: loss begins."""
        k1, k2, k3, credit = 440, 445, 455, 2.0
        payoff = self.calculate_payoff_at_expiry(spot=455, k1=k1, k2=k2, k3=k3, credit=credit)
        # At 455: long_k1 = 15, short_k2 = -20, long_k3 = 0
        # intrinsic = 15 - 20 + 0 = -5, P&L = (2 - 5) * 100 = -300
        assert payoff == -300.0
    
    def test_payoff_above_k3(self):
        """Above K3: max loss (constant)."""
        k1, k2, k3, credit = 440, 445, 455, 2.0
        payoff_460 = self.calculate_payoff_at_expiry(spot=460, k1=k1, k2=k2, k3=k3, credit=credit)
        payoff_500 = self.calculate_payoff_at_expiry(spot=500, k1=k1, k2=k2, k3=k3, credit=credit)
        # Above K3, all intrinsic values net to (k1 + k3 - 2*k2) = 440 + 455 - 890 = 5 - 10 = -5
        # Max loss = -300 regardless of how far above K3
        assert payoff_460 == -300.0
        assert payoff_500 == -300.0
    
    def test_max_profit_matches_calculator(self):
        """Verify calculator's max_profit matches actual payoff at K2."""
        k1, k2, k3, credit = 440, 445, 455, 2.0
        wing_left = k2 - k1
        
        calculator = BWBCalculator()
        calculated_max_profit = calculator.calculate_max_profit(credit, wing_left)
        actual_payoff_at_k2 = self.calculate_payoff_at_expiry(spot=k2, k1=k1, k2=k2, k3=k3, credit=credit)
        
        assert calculated_max_profit == actual_payoff_at_k2
    
    def test_max_loss_matches_calculator(self):
        """Verify calculator's max_loss matches actual payoff above K3."""
        k1, k2, k3, credit = 440, 445, 455, 2.0
        wing_left = k2 - k1
        wing_right = k3 - k2
        
        calculator = BWBCalculator()
        calculated_max_loss = calculator.calculate_max_loss(wing_left, wing_right, credit)
        actual_payoff_above_k3 = self.calculate_payoff_at_expiry(spot=500, k1=k1, k2=k2, k3=k3, credit=credit)
        
        assert calculated_max_loss == -actual_payoff_above_k3  # max_loss is positive, payoff is negative
    
    def test_larger_left_wing_no_upside_loss(self):
        """When left wing > right wing, no loss above K3."""
        k1, k2, k3, credit = 440, 450, 455, 2.0  # left=10, right=5
        wing_left = k2 - k1
        wing_right = k3 - k2
        
        payoff_above_k3 = self.calculate_payoff_at_expiry(spot=500, k1=k1, k2=k2, k3=k3, credit=credit)
        # intrinsic = (500-440) - 2*(500-450) + (500-455) = 60 - 100 + 45 = 5
        # P&L = (2 + 5) * 100 = 700 (profit, not loss!)
        assert payoff_above_k3 == 700.0
        
        calculator = BWBCalculator()
        max_loss = calculator.calculate_max_loss(wing_left, wing_right, credit)
        assert max_loss == 0.0  # No loss scenario for credit position with larger left wing
    
    def test_known_example_2(self):
        """Test 450/460/465 call BWB (larger left wing) with zero credit."""
        calculator = BWBCalculator()
        
        k1, k2, k3 = 450, 460, 465
        wing_left = k2 - k1  # 10
        wing_right = k3 - k2  # 5
        ask_k1, bid_k2, ask_k3 = 18.0, 12.0, 6.0
        
        credit = calculator.calculate_credit(ask_k1, bid_k2, ask_k3)
        max_profit = calculator.calculate_max_profit(credit, wing_left)
        max_loss = calculator.calculate_max_loss(wing_left, wing_right, credit)
        score = calculator.calculate_score(max_profit, max_loss)
        
        assert credit == 0.0
        assert max_profit == 1000.0  # (0 + 10) * 100
        # Max loss = (5 - 10 - 0) * 100 = -500, clamped to 0
        assert max_loss == 0.0
        assert score == 100.0  # No loss = max score
    
    def test_known_example_3_with_credit(self):
        """Test 450/460/465 BWB with $3 credit."""
        calculator = BWBCalculator()
        
        k1, k2, k3 = 450, 460, 465
        wing_left = k2 - k1  # 10
        wing_right = k3 - k2  # 5
        ask_k1, bid_k2, ask_k3 = 16.0, 12.0, 5.0
        
        credit = calculator.calculate_credit(ask_k1, bid_k2, ask_k3)
        max_profit = calculator.calculate_max_profit(credit, wing_left)
        max_loss = calculator.calculate_max_loss(wing_left, wing_right, credit)
        
        assert credit == 3.0
        assert max_profit == 1300.0  # (3 + 10) * 100
        # Max loss = (5 - 10 - 3) * 100 = -800, clamped to 0
        assert max_loss == 0.0
    
    def test_payoff_at_expiration_at_k2(self):
        """Test max profit at K2 includes intrinsic value of left wing."""
        calculator = BWBCalculator()
        # 440/445/455: wing_left = 5, credit = 2
        max_profit = calculator.calculate_max_profit(credit=2.0, wing_left=5.0)
        assert max_profit == 700.0
    
    def test_payoff_at_expiration_above_k3(self):
        """Test max loss above K3."""
        calculator = BWBCalculator()
        # 440/445/455: wing_left = 5, wing_right = 10, credit = 2
        max_loss = calculator.calculate_max_loss(wing_left=5.0, wing_right=10.0, credit=2.0)
        assert max_loss == 300.0


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
            "bid": [14.5, 11.5, 8.5, 5.5, 3.5, 2.0, 1.0, 0.5, 0.3, 0.1],
            "ask": [15.5, 12.5, 9.5, 6.5, 4.5, 3.0, 2.0, 1.5, 1.0, 0.8],
            "mid": [15.0, 12.0, 9.0, 6.0, 4.0, 2.5, 1.5, 1.0, 0.65, 0.45],
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
        
        data = {
            "symbol": ["SPY"] * 5,
            "expiry": ["2025-11-30"] * 5,
            "dte": [5] * 5,
            "strike": [440.0, 445.0, 450.0, 455.0, 460.0],
            "type": ["call"] * 5,
            "bid": [19.5, 14.5, 9.5, 5.5, 2.5],
            "ask": [20.5, 15.5, 10.5, 6.5, 3.5],
            "mid": [20.0, 15.0, 10.0, 6.0, 3.0],
            "delta": [0.70, 0.50, 0.30, 0.20, 0.10],
            "iv": [0.20] * 5
        }
        chain = pd.DataFrame(data)
        
        positions = constructor.find_all_combinations(chain)
        if len(positions) > 0:
            for pos in positions:
                assert abs(pos.wing_left - pos.wing_right) > 0.001
    
    def test_zero_max_loss_edge_case(self):
        """Test score calculation when max_loss is zero."""
        calculator = BWBCalculator()
        score = calculator.calculate_score(max_profit=100.0, max_loss=0.0)
        assert score == 100.0, "Score should be 100 when max_loss is 0 (best possible)"