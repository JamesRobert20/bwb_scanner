from typing import Annotated, Optional
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from .strategy import BWBConstructor
from .data_generator import OptionsChainGenerator
import pandas as pd
import os

app = FastAPI(
    title="BWB Scanner API",
    description="REST API for Broken Wing Butterfly options strategy scanner",
    version="1.0.0"
)

origins_env = os.getenv("ALLOWED_ORIGINS", "*")
origins = origins_env.split(",") if origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins_env != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)


# Cache the generated chain data in memory
_cached_chain: Optional[pd.DataFrame] = None


def get_options_chain() -> pd.DataFrame:
    """
    Get options chain data (generates in-memory, no file I/O).
    
    Returns:
        DataFrame with options chain data
    """
    global _cached_chain
    
    if _cached_chain is None:
        generator = OptionsChainGenerator(ticker="SPY")
        _cached_chain = generator.generate_chain(spot_price=450.0)
    
    return _cached_chain


def scan_chain(chain_data: pd.DataFrame, ticker: str, expiry: Optional[str] = None) -> pd.DataFrame:
    """
    Scan options chain for BWB opportunities.
    
    Args:
        chain_data: Options chain DataFrame
        ticker: Ticker symbol
        expiry: Optional specific expiry date
        
    Returns:
        DataFrame with valid BWB positions
    """
    constructor = BWBConstructor()
    
    # Filter by ticker
    filtered = chain_data[chain_data["symbol"] == ticker.upper()].copy()
    
    if filtered.empty:
        return pd.DataFrame(columns=[
            "ticker", "expiry", "dte", "k1", "k2", "k3",
            "wing_left", "wing_right", "credit", "max_profit",
            "max_loss", "score"
        ])
    
    # Filter by expiry if specified
    if expiry:
        filtered = filtered[filtered["expiry"] == expiry]
    
    # Get all expiries to scan
    expiries = filtered["expiry"].unique()
    
    all_results = []
    for exp in expiries:
        expiry_data = filtered[filtered["expiry"] == exp]
        calls_only = expiry_data[expiry_data["type"] == "call"]
        
        if calls_only.empty:
            continue
            
        positions = constructor.find_all_combinations(calls_only)
        
        if positions:
            results_df = pd.DataFrame([pos.to_dict() for pos in positions])
            all_results.append(results_df)
    
    if not all_results:
        return pd.DataFrame(columns=[
            "ticker", "expiry", "dte", "k1", "k2", "k3",
            "wing_left", "wing_right", "credit", "max_profit",
            "max_loss", "score"
        ])
    
    combined = pd.concat(all_results, ignore_index=True)
    combined = combined.sort_values("score", ascending=False).reset_index(drop=True)
    
    return combined




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
    # Get options chain data (in-memory, no file I/O)
    chain_data = get_options_chain()
    
    # Perform scan
    results = scan_chain(chain_data, ticker, expiry)
    
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