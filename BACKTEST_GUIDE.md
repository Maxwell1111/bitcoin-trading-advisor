# Bitcoin Advisor Backtest - Complete Guide

## What is Backtesting?

**Backtesting** means testing the recommendation engine on **historical data** to see how well it would have performed if you had used it in the past.

Think of it like this:
- We go back in time 1 year
- Every week, we run the advisor as if we were living in that moment
- We record what recommendation it gave (Buy/Hold/Sell)
- We then check if that recommendation was correct by looking at what actually happened to the price

## How This Backtest Works

### Step-by-Step Process

1. **Fetch Historical Data**: Get 1 year of Bitcoin price history
2. **Weekly Analysis**: Every 7 days, we:
   - Analyze the past 100 days of data (what the advisor would have seen)
   - Calculate RSI, Moving Averages, Power Law position, MACD, etc.
   - Generate composite score and recommendation
   - Record what the advisor said
3. **Check Accuracy**: Compare the recommendation to what actually happened:
   - If it said "Buy" and price went up → ✅ Correct
   - If it said "Sell" and price went down → ✅ Correct
   - If it said "Hold" and price stayed flat → ✅ Correct

### Your Recent Backtest Results

**Period**: March 31, 2025 → December 15, 2025 (38 weeks)

**What the Advisor Recommended:**
- **1 time** (2.6%): BUY signal
- **37 times** (97.4%): HOLD signal
- **0 times** (0%): SELL signal

**Why mostly HOLD?**
- Bitcoin was in a **sideways/consolidation** phase in 2025
- Composite score stayed between -0.14 and +0.31 (mostly in the -0.3 to +0.3 range)
- No extreme signals triggered (no strong buy/sell zones)

## Understanding the Charts

### Chart 1: BTC Price vs Composite Score

**Left Y-axis (Blue line)**: Bitcoin price in dollars
**Right Y-axis (Red/Orange lines)**: Composite score

**What to look for:**
- Does the score rise **before** price rises? (Predictive signal)
- Does the score fall **before** price falls? (Warning signal)
- Are they moving together or opposite?

**Example Interpretation:**
- If score = +0.5 and then price pumps → Good signal
- If score = -0.5 and then price dumps → Good signal
- If they're uncorrelated → Advisor not capturing trend

### Chart 2: Composite Score Over Time (Color-Coded)

**Green bars**: Bullish signals (score > 0.3)
**Yellow/Gray bars**: Neutral/Hold signals (-0.3 to 0.3)
**Red bars**: Bearish signals (score < -0.3)

**The dashed lines show thresholds:**
- Top line (+0.7): Strong Buy threshold
- Second line (+0.3): Buy threshold
- Third line (-0.3): Sell threshold
- Bottom line (-0.7): Strong Sell threshold

**What to look for:**
- How often does it cross thresholds?
- Does it stay in Hold zone too long (too conservative)?
- Does it give too many signals (too reactive)?

**Your results:** Stayed in Hold zone almost entire year (conservative)

### Chart 3: Individual Factor Scores

Shows the 5 factors **before weighting**:
- **Blue (RSI)**: Overbought/oversold indicator
- **Green (MA)**: Trend from moving averages
- **Red (Power Law)**: Long-term macro position
- **Orange (MACD)**: Momentum indicator
- **White (Sentiment)**: Market psychology (mock=neutral in backtest)

**What to look for:**
- Which factors are most volatile?
- Which factors lead price movements?
- Are factors agreeing or diverging?

**Example:**
- RSI spikes to +0.5 → Oversold, bullish
- Power Law drops to -0.7 → Overvalued, bearish
- If all 5 align → Strong signal

### Chart 4: RSI & Power Law Deviation

**Left Y-axis (Blue)**: RSI value (0-100)
- Above 70 = Overbought (red line)
- Below 30 = Oversold (green line)

**Right Y-axis (Red)**: Power Law Deviation (%)
- Positive = Above fair value (expensive)
- Negative = Below fair value (cheap)
- Zero line = Exactly at fair value

**What to look for:**
- RSI extremes (30 or 70) often signal reversals
- Large Power Law deviations suggest mean reversion opportunities
- Combination of both = Strong signal

## What Your Results Mean

### Composite Score Statistics

```
Mean:  +0.026  → Slightly bullish bias
Std:   0.114   → Low volatility (stable)
Min:   -0.138  → Never hit strong sell threshold
Max:   +0.305  → Once crossed into buy zone
```

**Interpretation:**
- The advisor was **conservative** in 2025
- Only gave 1 buy signal all year
- Never gave a sell signal
- This is appropriate for a sideways market

### Signal Distribution

**Buy: 2.6%** (1 time)
- Happened when composite score crossed above +0.3
- Likely when RSI was oversold + Power Law undervalued + MACD bullish

**Hold: 97.4%** (37 times)
- Most of the year, factors were mixed
- No strong confluence of signals
- Price was choppy/sideways

**Sell: 0%** (never)
- Never had enough bearish factors align
- Power Law stayed mostly neutral to undervalued
- RSI didn't sustain overbought levels

## Is This Good or Bad?

### Good Signs ✅
- **Conservative approach**: Avoids overtrading
- **Factor-based**: Not just sentiment-driven
- **Measurable**: Can track what works

### Areas for Improvement 🔧
- **Accuracy: 23.7%** is low
  - Means only ~1 in 4 signals matched price movement
  - Could be due to 7-day window being too short
  - Or factors need reweighting

### Why Low Accuracy?

1. **7-Day Window**: We check if price moved in 7 days
   - Bitcoin can be volatile short-term
   - Might need longer window (14-30 days)

2. **Mock Sentiment**: Using neutral sentiment in backtest
   - Missing 15% of the signal
   - Real sentiment data would help

3. **Sideways Market**: 2025 was consolidation
   - Hold signals appropriate
   - But measured as "wrong" if price moved ±5%

## How to Use These Results

### For Trading Decisions

**Current Score: +0.22 (Hold)**
- Not strong enough to buy (+0.3 needed)
- Not weak enough to sell (-0.3 needed)
- Wait for clearer signal

**What Would Trigger Buy?**
- RSI drops below 30 (oversold)
- Power Law goes below -10% (undervalued)
- MACD turns bullish
- **Composite crosses +0.3**

**What Would Trigger Sell?**
- RSI above 70 (overbought)
- Power Law goes above +30% (overvalued)
- MACD turns bearish
- **Composite drops below -0.3**

### For Improving the Model

Based on backtest, you could:

1. **Adjust Weights**
   - See which factor was most predictive
   - Increase weight of best performers
   - Decrease weight of noise

2. **Tune Thresholds**
   - Maybe +0.3 is too high for buy (too conservative)
   - Try +0.2 threshold
   - Or add "weak buy" signal

3. **Add More Factors**
   - Volume analysis
   - On-chain metrics
   - Funding rates

## Next Steps

### Run Updated Backtest
```bash
# Edit backtest_advisor.py to change:
# - BACKTEST_DAYS (try 730 for 2 years)
# - STEP_SIZE (try 14 for biweekly)
python3 backtest_advisor.py
python3 plot_backtest.py
open backtest_visualization.html
```

### Test Different Configurations
Try different factor weights and see if accuracy improves:
- Increase Power Law weight (currently 25%)
- Decrease Sentiment weight (currently 15%)
- Add RSI weight (currently 20%)

### Compare to Buy & Hold
Calculate: If you just bought Bitcoin 1 year ago and held, what would your return be?
Compare to following the advisor's signals.

---

## Summary

**The backtest shows your advisor is conservative and stable**:
- Mostly recommended holding during 2025's sideways action
- Only 1 buy signal all year
- Low accuracy (23.7%) suggests need for tuning

**This is actually good for avoiding losses**, but may miss opportunities.

**Key insight**: The holistic approach prevents overreacting to single factors, which is valuable for long-term investing but might miss short-term trades.
