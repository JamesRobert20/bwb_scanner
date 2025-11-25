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

# Configure CORS for development (allow all origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_options_chain() -> BWBScanner:
    """
    Load the options chain data and return scanner instance.
    
    Returns:
        Initialized BWBScanner instance
    """
    return BWBScanner("sample_options_chain.csv")


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