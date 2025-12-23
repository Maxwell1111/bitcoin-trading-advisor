
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict

class PowerLawModel:
    """
    Implements the Bitcoin Power Law (BPL) model and corridor analysis.
    Formula: Price = 10**-17 * (days_since_genesis**5.8)
    """

    def __init__(self, corridor_offset: float = 0.6):
        """
        Initializes the model.
        Args:
            corridor_offset: The offset in log10 space to define the upper and lower bands.
                             A value of 0.6 means the resistance band is 10^0.6 (~4x) the fair value,
                             and the support band is 1/4th the fair value.
        """
        self.genesis_date = datetime(2009, 1, 3)
        self.corridor_offset = corridor_offset

    def _calculate_bpl_value(self, days_since_genesis: np.ndarray) -> np.ndarray:
        """Calculates the BPL fair value."""
        # The formula is Price = A * (days^N)
        # In log-log space, log(Price) = log(A) + N * log(days)
        # With A = 10^-17 and N = 5.8
        log_A = -17
        N = 5.8
        log_days = np.log10(days_since_genesis)
        log_price = log_A + N * log_days
        return 10**log_price

    def analyze(self, historical_data: pd.DataFrame) -> Dict:
        """
        Analyzes historical price data against the Power Law model.

        Args:
            historical_data: A pandas DataFrame with a 'Close' price column and a DatetimeIndex.

        Returns:
            A dictionary containing the analysis results.
        """
        if not isinstance(historical_data.index, pd.DatetimeIndex):
            raise ValueError("historical_data must have a DatetimeIndex.")

        # Handle timezone-aware and timezone-naive datetime objects
        index = historical_data.index
        genesis = self.genesis_date

        # If index is timezone-aware, make genesis timezone-aware too
        if index.tz is not None:
            import pytz
            genesis = pytz.UTC.localize(self.genesis_date)

        days_since_genesis = (index - genesis).days.values

        # Calculate the three corridor lines
        fair_value_line = self._calculate_bpl_value(days_since_genesis)
        
        # Calculate bands in log space and convert back
        log_fair_value = np.log10(fair_value_line)
        log_resistance = log_fair_value + self.corridor_offset
        log_support = log_fair_value - self.corridor_offset
        
        resistance_line = 10**log_resistance
        support_line = 10**log_support

        # Get the latest price and band values
        # Handle both 'Close' and 'close' column names
        close_col = 'Close' if 'Close' in historical_data.columns else 'close'
        current_price = historical_data[close_col].iloc[-1]
        current_fair_value = fair_value_line[-1]
        current_support = support_line[-1]
        current_resistance = resistance_line[-1]

        # Determine the current status
        status = "Fair Value Zone"
        if current_price < current_support:
            status = "Deep Value"
        elif current_price > current_resistance:
            status = "Bubble Risk"
        
        # Check for mean reversion pressure
        mean_reversion_narrative = ""
        # Using log space for a more stable distance metric
        log_current = np.log10(current_price)
        log_fair = np.log10(current_fair_value)
        # If price is more than halfway to a band, suggest mean reversion
        if abs(log_current - log_fair) > self.corridor_offset * 0.5:
             direction = "down" if log_current > log_fair else "up"
             mean_reversion_narrative = f"The current price is significantly deviated from the long-term fair value line. A reversion to the mean ({direction}wards) is mathematically probable over the medium term (6-12 months)."


        return {
            "status": status,
            "current_price": current_price,
            "fair_value": current_fair_value,
            "support_value": current_support,
            "resistance_value": current_resistance,
            "mean_reversion_narrative": mean_reversion_narrative,
            "time_series": {
                "dates": historical_data.index.strftime('%Y-%m-%d').tolist(),
                "market_price": historical_data[close_col].tolist(),
                "fair_value_line": fair_value_line.tolist(),
                "support_line": support_line.tolist(),
                "resistance_line": resistance_line.tolist(),
            }
        }
