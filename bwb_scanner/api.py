"""
FastAPI application for BWB Scanner.
Provides REST API endpoints for the Next.js frontend.
"""

from typing import Annotated, Optional
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from .scanner import BWBScanner
import pandas as pd


app = FastAPI(
    title="BWB Scanner API",
    description="REST API for Broken Wing Butterfly options strategy scanner",
    version="1.0.0"
)

# Configure CORS
import os

# Get allowed origins from environment variable
# For production, set ALLOWED_ORIGINS in Vercel: "https://your-frontend.vercel.app,https://your-custom-domain.com"
# For development, defaults to allow all origins
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")

if allowed_origins_env == "*":
    # Development: allow all origins (can't use credentials with wildcard)
    allow_origins = ["*"]
    allow_credentials = False
else:
    # Production: specific origins (can use credentials)
    allow_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def load_options_chain() -> BWBScanner:
    """
    Load the options chain data and return scanner instance.
    
    Returns:
        Initialized BWBScanner instance
    """
    import os
    from pathlib import Path
    
    # Try to find the CSV file in various locations
    csv_paths = [
        "sample_options_chain.csv",
        os.path.join(os.path.dirname(__file__), "..", "sample_options_chain.csv"),
        os.path.join(os.path.dirname(__file__), "..", "..", "sample_options_chain.csv"),
        "/var/task/sample_options_chain.csv",  # Vercel/Lambda path
    ]
    
    csv_path = None
    for path in csv_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    # If file doesn't exist, generate it
    if csv_path is None:
        from .data_generator import OptionsChainGenerator
        csv_path = "sample_options_chain.csv"
        generator = OptionsChainGenerator(ticker="SPY")
        chain = generator.generate_chain(spot_price=450.0)
        generator.save_to_csv(chain, csv_path)
    
    return BWBScanner(csv_path)


@app.get("/")
async def root():
    """
    Root endpoint - API health check.
    
    Returns:
        Simple message confirming API is ready
    """
    return {"message": "BWB Scanner API ready"}


@app.post("/scan")
async def scan_bwb(
    ticker: Annotated[str, Body()],
    expiry: Annotated[Optional[str], Body()] = None
):
    """
    Scan for BWB opportunities.
    
    Args:
        ticker: Ticker symbol to scan (e.g., "SPY")
        expiry: Optional expiry date in YYYY-MM-DD format
        
    Returns:
        JSON with results and summary statistics
    """
    # Load scanner with default filters
    scanner = load_options_chain()
    
    # Perform scan
    if expiry:
        results = scanner.scan(ticker, expiry)
    else:
        results = scanner.scan_all_expiries(ticker)
    
    # Convert results to dict
    if results.empty:
        results_list = []
        summary = {
            "total_found": 0,
            "avg_score": 0.0,
            "best_score": 0.0,
            "avg_credit": 0.0
        }
    else:
        results_list = results.to_dict(orient="records")
        summary = {
            "total_found": len(results),
            "avg_score": round(results["score"].mean(), 4),
            "best_score": round(results["score"].max(), 4),
            "avg_credit": round(results["credit"].mean(), 2)
        }
    
    return {
        "results": results_list,
        "summary": summary
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns:
        Status information
    """
    return {
        "status": "healthy",
        "service": "bwb-scanner-api",
        "version": "1.0.0"
    }