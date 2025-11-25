"""
Example script demonstrating programmatic usage of the BWB Scanner.
"""

from bwb_scanner.scanner import BWBScanner
from bwb_scanner.strategy import BWBValidator
from bwb_scanner.data_generator import OptionsChainGenerator


def example_generate_and_scan():
    """Example: Generate sample data and scan for BWB opportunities."""
    
    print("=" * 80)
    print("BWB Scanner - Programmatic Usage Example")
    print("=" * 80)
    
    # Step 1: Generate sample data
    print("\n1. Generating sample options chain data...")
    generator = OptionsChainGenerator(ticker="SPY", seed=42)
    chain = generator.generate_chain(spot_price=450.0, dte_list=[3, 5, 7, 10])
    csv_path = "example_chain.csv"
    generator.save_to_csv(chain, csv_path)
    print(f"   Generated {len(chain)} options")
    print(f"   Saved to: {csv_path}")
    
    # Step 2: Create scanner with custom validator
    print("\n2. Creating scanner with custom parameters...")
    custom_validator = BWBValidator(
        min_dte=3,
        max_dte=7,
        min_delta=0.25,
        max_delta=0.35,
        min_credit=1.00
    )
    scanner = BWBScanner(csv_path, validator=custom_validator)
    print("   Scanner initialized with custom validator:")
    print(f"   - DTE range: {custom_validator.min_dte}-{custom_validator.max_dte} days")
    print(f"   - Delta range: {custom_validator.min_delta}-{custom_validator.max_delta}")
    print(f"   - Min credit: ${custom_validator.min_credit}")
    
    # Step 3: Scan for opportunities
    print("\n3. Scanning for BWB opportunities...")
    results = scanner.scan_all_expiries("SPY")
    print(f"   Found {len(results)} valid positions")
    
    # Step 4: Display top results
    if not results.empty:
        print("\n4. Top 5 BWB Positions:")
        print("-" * 80)
        top_5 = results.head(5)
        for idx, row in top_5.iterrows():
            print(f"\n   Position #{idx + 1}:")
            print(f"   Strikes: {row['k1']:.0f} / {row['k2']:.0f} / {row['k3']:.0f}")
            print(f"   Wings: {row['wing_left']:.0f} x {row['wing_right']:.0f}")
            print(f"   Expiry: {row['expiry']} ({row['dte']} DTE)")
            print(f"   Credit: ${row['credit']:.2f}")
            print(f"   Max Profit: ${row['max_profit']:.2f}")
            print(f"   Max Loss: ${row['max_loss']:.2f}")
            print(f"   Score: {row['score']:.4f}")
        
        # Step 5: Show summary statistics
        print("\n5. Summary Statistics:")
        print("-" * 80)
        stats = scanner.get_summary_stats(results)
        for key, value in stats.items():
            print(f"   {key.replace('_', ' ').title()}: {value}")
        
        # Step 6: Save results
        output_file = "example_results.csv"
        results.to_csv(output_file, index=False)
        print(f"\n6. Full results saved to: {output_file}")
    else:
        print("\n   No valid positions found with current criteria.")
    
    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


def example_scan_specific_expiry():
    """Example: Scan a specific expiry only."""
    
    print("\n\nScanning specific expiry example...")
    print("-" * 80)
    
    scanner = BWBScanner("sample_options_chain.csv")
    results = scanner.scan("SPY", "2025-11-29")
    
    print(f"Found {len(results)} positions for expiry 2025-11-29")
    
    if not results.empty:
        best = results.iloc[0]
        print(f"\nBest position:")
        print(f"  {best['k1']:.0f} / {best['k2']:.0f} / {best['k3']:.0f}")
        print(f"  Score: {best['score']:.4f}")
        print(f"  Credit: ${best['credit']:.2f}")


if __name__ == "__main__":
    # Run the main example
    example_generate_and_scan()
    
    # Run the specific expiry example
    example_scan_specific_expiry()