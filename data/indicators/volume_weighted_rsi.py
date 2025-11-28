"""
Volume Weighted RSI

RSI weighted by relative volume to emphasize moves on high volume

Parameters: {
  "period": 14,
  "vol_period": 20
}

Usage:
df["vw_rsi"] = calculate_vw_rsi(df)
"""

def calculate_vw_rsi(df, period=14, vol_period=20):
    """Volume-weighted RSI indicator."""
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rsi = 100 - (100 / (1 + gain / loss))
    
    vol_sma = df["volume"].rolling(vol_period).mean()
    vol_weight = df["volume"] / vol_sma
    
    return rsi * vol_weight