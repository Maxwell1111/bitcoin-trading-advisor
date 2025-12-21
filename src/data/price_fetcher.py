"""
Bitcoin price data fetcher
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional
import yfinance as yf


class PriceFetcher:
    """Fetch Bitcoin price data from various sources"""

    def __init__(self, provider: str = "coingecko"):
        """
        Initialize price fetcher

        Args:
            provider: Data provider ('coingecko', 'yfinance', or 'binance')
        """
        self.provider = provider.lower()

    def fetch_historical_data(self, days: int = 100, interval: str = "daily") -> pd.DataFrame:
        """
        Fetch historical price data

        Args:
            days: Number of days of historical data
            interval: Data interval ('daily', 'hourly')

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        if self.provider == "coingecko":
            return self._fetch_coingecko(days)
        elif self.provider == "yfinance":
            return self._fetch_yfinance(days)
        elif self.provider == "binance":
            return self._fetch_binance(days)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _fetch_coingecko(self, days: int) -> pd.DataFrame:
        """Fetch data from CoinGecko API"""
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Convert to DataFrame
            prices = data['prices']
            volumes = data['total_volumes']

            df = pd.DataFrame(prices, columns=['timestamp', 'close'])
            df['volume'] = [v[1] for v in volumes]
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # For CoinGecko, we only get close prices, so we approximate OHLC
            df['open'] = df['close']
            df['high'] = df['close']
            df['low'] = df['close']

            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df = df.set_index('timestamp')

            return df

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching data from CoinGecko: {e}")

    def _fetch_yfinance(self, days: int) -> pd.DataFrame:
        """Fetch data from Yahoo Finance"""
        try:
            # Yahoo Finance uses BTC-USD ticker
            btc = yf.Ticker("BTC-USD")

            # Calculate start date
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Fetch historical data
            df = btc.history(start=start_date, end=end_date)

            # Rename columns to match our format
            df.index.name = 'timestamp'
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # Select only needed columns
            df = df[['open', 'high', 'low', 'close', 'volume']]

            return df

        except Exception as e:
            raise Exception(f"Error fetching data from Yahoo Finance: {e}")

    def _fetch_binance(self, days: int) -> pd.DataFrame:
        """Fetch data from Binance API"""
        url = "https://api.binance.com/api/v3/klines"

        # Calculate timestamps
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        params = {
            'symbol': 'BTCUSDT',
            'interval': '1d',
            'startTime': start_time,
            'endTime': end_time,
            'limit': 1000
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Convert to DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            # Select and set index
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df = df.set_index('timestamp')

            return df

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching data from Binance: {e}")

    def get_current_price(self) -> float:
        """
        Get current Bitcoin price

        Returns:
            Current BTC price in USD
        """
        if self.provider == "coingecko":
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': 'bitcoin', 'vs_currencies': 'usd'}

            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                return data['bitcoin']['usd']
            except Exception as e:
                raise Exception(f"Error fetching current price: {e}")

        elif self.provider == "yfinance":
            try:
                btc = yf.Ticker("BTC-USD")
                return btc.info.get('regularMarketPrice', btc.info.get('currentPrice'))
            except Exception as e:
                raise Exception(f"Error fetching current price: {e}")

        else:
            # Get latest price from historical data
            df = self.fetch_historical_data(days=1)
            return df['close'].iloc[-1]


if __name__ == "__main__":
    # Test the price fetcher
    fetcher = PriceFetcher(provider="coingecko")

    print("Fetching current Bitcoin price...")
    current_price = fetcher.get_current_price()
    print(f"Current BTC Price: ${current_price:,.2f}")

    print("\nFetching historical data (last 30 days)...")
    df = fetcher.fetch_historical_data(days=30)
    print(df.tail())
    print(f"\nDataFrame shape: {df.shape}")
