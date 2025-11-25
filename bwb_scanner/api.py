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

generator = OptionsChainGenerator(ticker="SPY")
_chain_data = generator.generate_chain(spot_price=450.0, num_strikes=15)
_constructor = BWBConstructor()

_scan_cache: dict = {}

def scan_chain(ticker: str, expiry: Optional[str] = None) -> pd.DataFrame:
    cache_key = f"{ticker}:{expiry or 'all'}"
    if cache_key in _scan_cache:
        return _scan_cache[cache_key]
    
    empty_df = pd.DataFrame(columns=[
        "ticker", "expiry", "dte", "k1", "k2", "k3",
        "wing_left", "wing_right", "credit", "max_profit",
        "max_loss", "score"
    ])
    
    filtered = _chain_data[_chain_data["symbol"] == ticker.upper()].copy()
    
    if filtered.empty:
        return empty_df
    
    if expiry:
        filtered = filtered[filtered["expiry"] == expiry]
    
    expiries = filtered["expiry"].unique()
    
    all_results = []
    for exp in expiries:
        expiry_data = filtered[filtered["expiry"] == exp]
        calls_only = expiry_data[expiry_data["type"] == "call"]
        
        if calls_only.empty:
            continue
            
        positions = _constructor.find_all_combinations(calls_only)
        
        if positions:
            results_df = pd.DataFrame([pos.to_dict() for pos in positions])
            all_results.append(results_df)
    
    if not all_results:
        return empty_df
    
    combined = pd.concat(all_results, ignore_index=True)
    combined = combined.sort_values("score", ascending=False).reset_index(drop=True)
    
    _scan_cache[cache_key] = combined
    return combined




@app.get("/")
async def root():
    return {"message": "BWB Scanner API ready"}


@app.post("/scan")
async def scan_bwb(
    ticker: Annotated[str, Body()],
    expiry: Annotated[Optional[str], Body()] = None
):
    import time
    start = time.time()
    results = scan_chain(ticker, expiry)
    scan_time_ms = round((time.time() - start) * 1000)
    
    if results.empty:
        return {
            "results": [],
            "summary": {
                "total_found": 0,
                "avg_score": 0.0,
                "best_score": 0.0,
                "avg_credit": 0.0,
                "scan_time_ms": scan_time_ms
            }
        }
    
    return {
        "results": results.to_dict(orient="records"),
        "summary": {
            "total_found": len(results),
            "avg_score": round(results["score"].mean(), 4),
            "best_score": round(results["score"].max(), 4),
            "avg_credit": round(results["credit"].mean(), 2),
            "scan_time_ms": scan_time_ms
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "bwb-scanner-api",
        "version": "1.0.0"
    }