import yfinance as yf
import pandas as pd
from datetime import datetime
from utils.db import get_cached_stock_data, cache_stock_data  # NEW


def fetch_stock_data(ticker: str, period: str = "3mo") -> dict:
    """
    Fetches real-time and historical stock data for a given ticker.
    
    Args:
        ticker: Stock symbol e.g. 'AAPL', 'RELIANCE.NS', 'TCS.NS'
        period: Time period - '1d','5d','1mo','3mo','6mo','1y','2y','5y'
    
    Returns:
        Dictionary with stock info and historical data
    """
    # NEW: Check cache first — if fresh data exists, skip yfinance API call
    cached = get_cached_stock_data(ticker, period)
    if cached:
        return cached

    try:
        stock = yf.Ticker(ticker)
        
        # Get historical price data
        history = stock.history(period=period)
        
        if history.empty:
            return {"error": f"No data found for ticker '{ticker}'. Check if the symbol is correct."}
        
        # Get current info
        info = stock.info
        
        # Build clean response
        result = {
            "ticker": ticker.upper(),
            "company_name": info.get("longName", "N/A"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice", "N/A"),
            "currency": info.get("currency", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "volume": info.get("volume", "N/A"),
            "sector": info.get("sector", "N/A"),
            "period": period,
            "data_points": len(history),
            "start_date": str(history.index[0].date()),
            "end_date": str(history.index[-1].date()),
            "price_change_pct": round(
                ((history["Close"].iloc[-1] - history["Close"].iloc[0]) / history["Close"].iloc[0]) * 100, 2
            ),
            "avg_volume": round(history["Volume"].mean(), 0),
            "highest_price": round(history["High"].max(), 2),
            "lowest_price": round(history["Low"].min(), 2),
            "history": history[["Open", "Close", "High", "Low", "Volume"]].tail(10).to_dict(orient="records")
        }

        # NEW: Save to cache so next request for same ticker+period is instant
        cache_stock_data(ticker, period, result)
        
        return result

    except Exception as e:
        return {"error": str(e)}


# ---- Test it directly ----
if __name__ == "__main__":
    from rich import print
    
    print("\n[bold cyan]Testing AlphaAgent Data Fetcher...[/bold cyan]\n")
    
    # Test with an Indian stock
    data = fetch_stock_data("RELIANCE.NS", period="3mo")
    print(data)