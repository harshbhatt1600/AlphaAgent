import pandas as pd
import yfinance as yf
import numpy as np

def detect_anomalies(ticker: str, period: str = "6mo", z_threshold: float = 2.0) -> dict:
    """
    Detects unusual price and volume activity in a stock.
    Uses Z-Score method — flags anything beyond z_threshold standard deviations.
    
    Args:
        ticker: Stock symbol e.g. 'RELIANCE.NS'
        period: Historical period to analyze
        z_threshold: How many standard deviations = anomaly (default 2)
    
    Returns:
        Dictionary with detected anomalies and summary
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)

        if df.empty:
            return {"error": f"No data found for {ticker}"}

        # --- Volume Anomaly Detection ---
        df["Volume_Mean"] = df["Volume"].rolling(window=20).mean()
        df["Volume_Std"] = df["Volume"].rolling(window=20).std()
        df["Volume_ZScore"] = (df["Volume"] - df["Volume_Mean"]) / df["Volume_Std"]

        # --- Price Change Anomaly Detection ---
        df["Price_Change_Pct"] = df["Close"].pct_change() * 100
        df["Price_Mean"] = df["Price_Change_Pct"].rolling(window=20).mean()
        df["Price_Std"] = df["Price_Change_Pct"].rolling(window=20).std()
        df["Price_ZScore"] = (df["Price_Change_Pct"] - df["Price_Mean"]) / df["Price_Std"]

        # --- Flag Anomalies ---
        volume_anomalies = df[df["Volume_ZScore"].abs() > z_threshold].copy()
        price_anomalies = df[df["Price_ZScore"].abs() > z_threshold].copy()

        # --- Format Results ---
        def format_anomalies(anomaly_df, z_col, value_col):
            results = []
            for date, row in anomaly_df.iterrows():
                results.append({
                    "date": str(date.date()),
                    "value": round(row[value_col], 2),
                    "z_score": round(row[z_col], 2),
                    "severity": "HIGH" if abs(row[z_col]) > 3 else "MODERATE"
                })
            return results

        volume_anomaly_list = format_anomalies(volume_anomalies, "Volume_ZScore", "Volume")
        price_anomaly_list = format_anomalies(price_anomalies, "Price_ZScore", "Price_Change_Pct")

        result = {
            "ticker": ticker.upper(),
            "period_analyzed": period,
            "total_trading_days": len(df),
            "volume_anomalies": {
                "count": len(volume_anomaly_list),
                "events": volume_anomaly_list[-5:]  # last 5 anomalies
            },
            "price_anomalies": {
                "count": len(price_anomaly_list),
                "events": price_anomaly_list[-5:]  # last 5 anomalies
            },
            "summary": f"Found {len(volume_anomaly_list)} volume anomalies and {len(price_anomaly_list)} price anomalies in the last {period} for {ticker.upper()}"
        }

        return result

    except Exception as e:
        return {"error": str(e)}


# ---- Test it ----
if __name__ == "__main__":
    from rich import print

    print("\n[bold cyan]Testing Anomaly Detection...[/bold cyan]\n")
    result = detect_anomalies("RELIANCE.NS", period="6mo")
    print(result)