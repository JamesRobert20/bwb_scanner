"""
Main entry point for BWB Scanner.
Demonstrates usage and provides CLI interface.
"""

import argparse
from pathlib import Path
from bwb_scanner.scanner import BWBScanner
from bwb_scanner.data_generator import OptionsChainGenerator


def generate_sample_data(output_path: str = "sample_options_chain.csv") -> None:
    """
    Generate sample options chain data.
    
    Args:
        output_path: Path to save the CSV file
    """
    print("Generating sample options chain data...")
    generator = OptionsChainGenerator(ticker="SPY")
    chain = generator.generate_chain(spot_price=450.0)
    generator.save_to_csv(chain, output_path)
    print(f"Sample data saved to: {output_path}")
    print(f"Total options generated: {len(chain)}")


def run_scanner(
    csv_path: str,
    ticker: str,
    expiry: str = None,
    show_stats: bool = True
) -> None:
    """
    Run the BWB scanner.
    
    Args:
        csv_path: Path to options chain CSV
        ticker: Ticker symbol to scan
        expiry: Specific expiry to scan (None for all)
        show_stats: Whether to show summary statistics
    """
    print(f"\nScanning for BWB opportunities in {ticker}...")
    print(f"Data source: {csv_path}\n")
    
    scanner = BWBScanner(csv_path)
    
    if expiry:
        results = scanner.scan(ticker, expiry)
        print(f"Scanning expiry: {expiry}")
    else:
        results = scanner.scan_all_expiries(ticker)
        print("Scanning all available expiries")
    
    print(f"\nFound {len(results)} valid BWB positions\n")
    
    if not results.empty:
        print("Top 10 BWB Positions (sorted by score):")
        print("=" * 100)
        
        # Display top 10 results
        display_cols = [
            "ticker", "expiry", "dte", "k1", "k2", "k3",
            "credit", "max_profit", "max_loss", "score"
        ]
        print(results[display_cols].head(10).to_string(index=False))
        
        if show_stats:
            print("\n" + "=" * 100)
            print("Summary Statistics:")
            print("=" * 100)
            stats = scanner.get_summary_stats(results)
            for key, value in stats.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        # Save results to CSV
        output_file = f"bwb_results_{ticker}.csv"
        results.to_csv(output_file, index=False)
        print(f"\nFull results saved to: {output_file}")
    else:
        print("No valid BWB positions found matching the criteria.")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BWB Scanner - Find Broken Wing Butterfly opportunities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate sample data
  python main.py --generate-sample
  
  # Scan using sample data
  python main.py --csv sample_options_chain.csv --ticker SPY
  
  # Scan specific expiry
  python main.py --csv sample_options_chain.csv --ticker SPY --expiry 2025-11-28
        """
    )
    
    parser.add_argument(
        "--generate-sample",
        action="store_true",
        help="Generate sample options chain data"
    )
    
    parser.add_argument(
        "--csv",
        type=str,
        help="Path to options chain CSV file"
    )
    
    parser.add_argument(
        "--ticker",
        type=str,
        help="Ticker symbol to scan"
    )
    
    parser.add_argument(
        "--expiry",
        type=str,
        help="Specific expiry date to scan (YYYY-MM-DD format)"
    )
    
    parser.add_argument(
        "--no-stats",
        action="store_true",
        help="Don't show summary statistics"
    )
    
    args = parser.parse_args()
    
    if args.generate_sample:
        generate_sample_data()
        return
    
    if not args.csv or not args.ticker:
        parser.print_help()
        print("\nError: --csv and --ticker are required (unless using --generate-sample)")
        return
    
    if not Path(args.csv).exists():
        print(f"Error: CSV file not found: {args.csv}")
        return
    
    run_scanner(
        csv_path=args.csv,
        ticker=args.ticker,
        expiry=args.expiry,
        show_stats=not args.no_stats
    )


if __name__ == "__main__":
    main()