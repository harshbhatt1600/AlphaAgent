import pandas as pd
import yfinance as yf
import ta

def calculate_indicators(ticker: str, period: str = "6mo") -> dict:
    """
    Calculates key technical indicators for a given stock.
    RSI, MACD, Bollinger Bands, Moving Averages.
    
    Args:
        ticker: Stock symbol e.g. 'AAPL', 'RELIANCE.NS'
        period: Time period for historical data
    
    Returns:
        Dictionary with all technical indicators
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)

        if df.empty:
            return {"error": f"No data found for {ticker}"}

        close = df["Close"]

        # --- Moving Averages ---
        df["MA_20"] = close.rolling(window=20).mean()
        df["MA_50"] = close.rolling(window=50).mean()

        # --- RSI (Relative Strength Index) ---
        # Measures momentum — above 70 = overbought, below 30 = oversold
        df["RSI"] = ta.momentum.RSIIndicator(close=close, window=14).rsi()

        # --- MACD (Moving Average Convergence Divergence) ---
        # Measures trend direction and strength
        macd = ta.trend.MACD(close=close)
        df["MACD"] = macd.macd()
        df["MACD_Signal"] = macd.macd_signal()
        df["MACD_Histogram"] = macd.macd_diff()

        # --- Bollinger Bands ---
        # Measures volatility
        bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        df["BB_Upper"] = bb.bollinger_hband()
        df["BB_Lower"] = bb.bollinger_lband()
        df["BB_Middle"] = bb.bollinger_mavg()

        # Get latest values only
        latest = df.iloc[-1]
        current_price = round(latest["Close"], 2)

        # --- Signal interpretation ---
        rsi_value = round(latest["RSI"], 2)
        if rsi_value > 70:
            rsi_signal = "OVERBOUGHT — potential sell zone"
        elif rsi_value < 30:
            rsi_signal = "OVERSOLD — potential buy zone"
        else:
            rsi_signal = "NEUTRAL"

        macd_signal = "BULLISH" if latest["MACD"] > latest["MACD_Signal"] else "BEARISH"

        ma_signal = "BULLISH" if latest["MA_20"] > latest["MA_50"] else "BEARISH"

        bb_position = "ABOVE UPPER BAND — overbought" if current_price > latest["BB_Upper"] \
            else "BELOW LOWER BAND — oversold" if current_price < latest["BB_Lower"] \
            else "WITHIN BANDS — normal range"

        result = {
            "ticker": ticker.upper(),
            "current_price": current_price,
            "moving_averages": {
                "MA_20": round(latest["MA_20"], 2),
                "MA_50": round(latest["MA_50"], 2),
                "signal": ma_signal
            },
            "RSI": {
                "value": rsi_value,
                "signal": rsi_signal
            },
            "MACD": {
                "macd": round(latest["MACD"], 4),
                "signal_line": round(latest["MACD_Signal"], 4),
                "histogram": round(latest["MACD_Histogram"], 4),
                "signal": macd_signal
            },
            "bollinger_bands": {
                "upper": round(latest["BB_Upper"], 2),
                "middle": round(latest["BB_Middle"], 2),
                "lower": round(latest["BB_Lower"], 2),
                "price_position": bb_position
            }
        }

        return result

    except Exception as e:
        return {"error": str(e)}


# ---- Test it directly ----
if __name__ == "__main__":
    from rich import print

    print("\n[bold cyan]Testing Technical Indicators...[/bold cyan]\n")
    result = calculate_indicators("RELIANCE.NS", period="6mo")
    print(result)