"""
Gold price data fetcher using yfinance (GLD ETF as proxy)
"""

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


class GoldFetcher:
    """Fetch Gold price data using GLD ETF as proxy"""

    def __init__(self, ticker: str = "GLD"):
        """
        Initialize gold fetcher

        Args:
            ticker: Gold ticker symbol (default: GLD ETF)
                   Alternatives: GC=F (Gold Futures), IAU (iShares Gold)
        """
        self.ticker = ticker

    def fetch_historical_data(self, days: int = 365) -> pd.DataFrame:
        """
        Fetch historical gold price data

        Args:
            days: Number of days of historical data

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        try:
            gold = yf.Ticker(self.ticker)

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            df = gold.history(start=start_date, end=end_date)

            if df.empty:
                raise Exception(f"No data returned for {self.ticker}")

            df.index.name = "timestamp"
            df = df.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )

            df = df[["open", "high", "low", "close", "volume"]]

            return df

        except Exception as e:
            raise Exception(f"Error fetching gold data: {e}")

    def get_current_price(self) -> float:
        """
        Get current gold price (GLD ETF)

        Returns:
            Current gold price in USD
        """
        try:
            gold = yf.Ticker(self.ticker)
            info = gold.info
            return info.get("regularMarketPrice", info.get("currentPrice", 0))
        except Exception as e:
            # Fallback: get latest close from history
            df = self.fetch_historical_data(days=5)
            if not df.empty:
                return df["close"].iloc[-1]
            raise Exception(f"Error fetching current gold price: {e}")


if __name__ == "__main__":
    # Test the gold fetcher
    fetcher = GoldFetcher()

    print("Fetching current Gold (GLD) price...")
    current_price = fetcher.get_current_price()
    print(f"Current GLD Price: ${current_price:,.2f}")

    print("\nFetching historical data (last 30 days)...")
    df = fetcher.fetch_historical_data(days=30)
    print(df.tail())
    print(f"\nDataFrame shape: {df.shape}")
