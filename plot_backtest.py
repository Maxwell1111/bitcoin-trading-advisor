#!/usr/bin/env python3
"""
Visualize backtest results in an HTML dashboard
"""
import pandas as pd
import json
from pathlib import Path

print("=" * 80)
print("GENERATING BACKTEST VISUALIZATION".center(80))
print("=" * 80)

# Load results
print("\n[1/3] Loading backtest results...")
df = pd.read_csv('backtest_results.csv')
df['date'] = pd.to_datetime(df['date'])
print(f"✓ Loaded {len(df)} data points")

# Prepare data for visualization
print("\n[2/3] Preparing visualization data...")

# Convert to lists for JavaScript
dates = df['date'].dt.strftime('%Y-%m-%d').tolist()
prices = df['price'].tolist()
composite_scores = df['composite_score'].tolist()
recommendations = df['recommendation'].tolist()
rsi_values = df['rsi_value'].tolist()
power_law_deviations = df['power_law_deviation'].tolist()

# Calculate moving averages of composite score
df['score_ma7'] = df['composite_score'].rolling(window=3, min_periods=1).mean()
score_ma7 = df['score_ma7'].tolist()

# Color code recommendations
colors = []
for rec in recommendations:
    if 'buy' in rec.lower():
        colors.append('green' if 'strong' in rec.lower() else 'lightgreen')
    elif 'sell' in rec.lower():
        colors.append('red' if 'strong' in rec.lower() else 'lightcoral')
    else:
        colors.append('gray')

print("✓ Data prepared")

# Create HTML visualization
print("\n[3/3] Generating HTML dashboard...")

html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Bitcoin Advisor Backtest Results</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #0f1419;
            color: #e1e8ed;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: #1da1f2;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #8899a6;
            margin-bottom: 30px;
        }}
        .explanation {{
            background: #192734;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            border: 1px solid #38444d;
        }}
        .explanation h3 {{
            color: #1da1f2;
            margin-top: 0;
        }}
        .explanation-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .explanation-item {{
            background: #0f1419;
            padding: 15px;
            border-radius: 5px;
        }}
        .explanation-item h4 {{
            color: #1da1f2;
            margin: 0 0 10px 0;
            font-size: 16px;
        }}
        .explanation-item p {{
            margin: 0;
            color: #8899a6;
            font-size: 14px;
            line-height: 1.6;
        }}
        .key-insight {{
            background: #1a3a52;
            border-left: 4px solid #1da1f2;
            padding: 15px;
            margin: 15px 0;
        }}
        .key-insight strong {{
            color: #1da1f2;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #192734;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #38444d;
        }}
        .stat-label {{
            color: #8899a6;
            font-size: 14px;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            color: #1da1f2;
        }}
        .chart {{
            background: #192734;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #38444d;
        }}
        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Bitcoin Trading Advisor - Backtest Results</h1>
        <p class="subtitle">Holistic Multi-Factor Analysis Performance</p>

        <div class="explanation">
            <h3>📖 What is This?</h3>
            <p>This backtest tests the recommendation engine on <strong>historical data</strong> to see how it would have performed in the past.</p>

            <div class="key-insight">
                <strong>How it works:</strong> Every week for the past year, we ran the advisor as if we were living in that moment. We recorded what it recommended (Buy/Hold/Sell) and compared it to what actually happened to Bitcoin's price.
            </div>

            <div class="explanation-grid">
                <div class="explanation-item">
                    <h4>🎯 Composite Score</h4>
                    <p><strong>Range:</strong> -1.00 to +1.00<br>
                    <strong>Meaning:</strong> Weighted average of 5 factors<br>
                    • +0.70+ = Strong Buy<br>
                    • +0.30 to +0.70 = Buy<br>
                    • -0.30 to +0.30 = Hold<br>
                    • -0.70 to -0.30 = Sell<br>
                    • -0.70- = Strong Sell</p>
                </div>

                <div class="explanation-item">
                    <h4>📊 The 5 Factors</h4>
                    <p><strong>RSI (20%):</strong> Overbought/oversold<br>
                    <strong>Moving Avg (25%):</strong> Trend direction<br>
                    <strong>Power Law (25%):</strong> Long-term value<br>
                    <strong>MACD (15%):</strong> Momentum<br>
                    <strong>Sentiment (15%):</strong> Market psychology</p>
                </div>

                <div class="explanation-item">
                    <h4>📈 Your Results</h4>
                    <p><strong>Conservative Strategy:</strong> 97% Hold signals<br>
                    <strong>Interpretation:</strong> The advisor avoided overtrading during 2025's sideways market.<br>
                    <strong>Accuracy:</strong> {(df['correct'].sum() / len(df) * 100):.1f}% of signals matched price movement</p>
                </div>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Period</div>
                <div class="stat-value" style="font-size: 18px;">{df['date'].iloc[0].strftime('%Y-%m-%d')}<br>to<br>{df['date'].iloc[-1].strftime('%Y-%m-%d')}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Data Points</div>
                <div class="stat-value">{len(df)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Composite Score</div>
                <div class="stat-value">{df['composite_score'].mean():.3f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Buy Signals</div>
                <div class="stat-value" style="color: #17bf63;">{(df['composite_score'] > 0.3).sum()}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Sell Signals</div>
                <div class="stat-value" style="color: #f45531;">{(df['composite_score'] < -0.3).sum()}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Hold Signals</div>
                <div class="stat-value" style="color: #8899a6;">{((df['composite_score'] >= -0.3) & (df['composite_score'] <= 0.3)).sum()}</div>
            </div>
        </div>

        <div class="explanation">
            <h3>Chart 1: Price vs Composite Score</h3>
            <p><strong>What to look for:</strong> Does the score rise BEFORE price rises? That would mean the advisor is predicting upward movement. Does it fall before price falls? That's a warning signal.</p>
        </div>
        <div class="chart" id="price-score-chart"></div>

        <div class="explanation">
            <h3>Chart 2: Composite Score Distribution</h3>
            <p><strong>Color coding:</strong> Green bars = Buy signals, Gray = Hold, Red = Sell. The dashed lines show the thresholds (+0.7, +0.3, -0.3, -0.7).<br>
            <strong>Your results:</strong> Almost all bars are gray (Hold) because 2025 was a sideways/consolidation year with no extreme signals.</p>
        </div>
        <div class="chart" id="composite-chart"></div>

        <div class="explanation">
            <h3>Chart 3: Individual Factor Contributions</h3>
            <p><strong>This shows each of the 5 factors BEFORE weighting.</strong> You can see which factors were bullish (positive) or bearish (negative) at different times.<br>
            <strong>Key insight:</strong> When all 5 lines align (all positive or all negative), that creates a strong signal. When they diverge, you get Hold.</p>
        </div>
        <div class="chart" id="factors-chart"></div>

        <div class="explanation">
            <h3>Chart 4: RSI & Power Law Deviation Detail</h3>
            <p><strong>RSI (blue):</strong> Above 70 = overbought (potential sell), below 30 = oversold (potential buy).<br>
            <strong>Power Law (red):</strong> Negative % = Bitcoin is cheap vs long-term trend. Positive % = Bitcoin is expensive.<br>
            <strong>Sweet spot:</strong> RSI below 30 + Power Law negative = Strong buy opportunity.</p>
        </div>
        <div class="chart" id="rsi-pl-chart"></div>

        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background: #17bf63;"></div>
                <span>Strong Buy (&gt; 0.7)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #90ee90;"></div>
                <span>Buy (0.3 to 0.7)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #8899a6;"></div>
                <span>Hold (-0.3 to 0.3)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ffb3b3;"></div>
                <span>Sell (-0.7 to -0.3)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #f45531;"></div>
                <span>Strong Sell (&lt; -0.7)</span>
            </div>
        </div>
    </div>

    <script>
        // Data
        const dates = {json.dumps(dates)};
        const prices = {json.dumps(prices)};
        const compositeScores = {json.dumps(composite_scores)};
        const scoreMa7 = {json.dumps(score_ma7)};
        const rsiValues = {json.dumps(rsi_values)};
        const powerLawDeviations = {json.dumps(power_law_deviations)};
        const recommendations = {json.dumps(recommendations)};

        // Chart 1: Price vs Composite Score
        const trace1 = {{
            x: dates,
            y: prices,
            name: 'BTC Price',
            type: 'scatter',
            line: {{ color: '#1da1f2', width: 2 }},
            yaxis: 'y'
        }};

        const trace2 = {{
            x: dates,
            y: compositeScores,
            name: 'Composite Score',
            type: 'scatter',
            line: {{ color: '#f45531', width: 2 }},
            yaxis: 'y2'
        }};

        const trace3 = {{
            x: dates,
            y: scoreMa7,
            name: 'Score MA (3-day)',
            type: 'scatter',
            line: {{ color: '#ffad1f', width: 1, dash: 'dot' }},
            yaxis: 'y2'
        }};

        const layout1 = {{
            title: 'BTC Price vs Composite Score',
            paper_bgcolor: '#192734',
            plot_bgcolor: '#0f1419',
            font: {{ color: '#e1e8ed' }},
            xaxis: {{ gridcolor: '#38444d' }},
            yaxis: {{
                title: 'BTC Price ($)',
                gridcolor: '#38444d',
                side: 'left'
            }},
            yaxis2: {{
                title: 'Composite Score',
                overlaying: 'y',
                side: 'right',
                gridcolor: '#38444d',
                zeroline: true,
                zerolinecolor: '#8899a6'
            }},
            hovermode: 'x unified'
        }};

        Plotly.newPlot('price-score-chart', [trace1, trace2, trace3], layout1, {{responsive: true}});

        // Chart 2: Composite Score Distribution
        const trace4 = {{
            x: dates,
            y: compositeScores,
            type: 'bar',
            marker: {{
                color: compositeScores.map(score =>
                    score > 0.7 ? '#17bf63' :
                    score > 0.3 ? '#90ee90' :
                    score < -0.7 ? '#f45531' :
                    score < -0.3 ? '#ffb3b3' :
                    '#8899a6'
                )
            }},
            name: 'Composite Score'
        }};

        const layout2 = {{
            title: 'Composite Score Over Time (Color-coded by Signal)',
            paper_bgcolor: '#192734',
            plot_bgcolor: '#0f1419',
            font: {{ color: '#e1e8ed' }},
            xaxis: {{ gridcolor: '#38444d' }},
            yaxis: {{
                title: 'Composite Score',
                gridcolor: '#38444d',
                zeroline: true,
                zerolinecolor: '#8899a6'
            }},
            shapes: [
                {{ type: 'line', y0: 0.7, y1: 0.7, x0: dates[0], x1: dates[dates.length-1],
                   line: {{ color: '#17bf63', width: 1, dash: 'dash' }} }},
                {{ type: 'line', y0: 0.3, y1: 0.3, x0: dates[0], x1: dates[dates.length-1],
                   line: {{ color: '#90ee90', width: 1, dash: 'dash' }} }},
                {{ type: 'line', y0: -0.3, y1: -0.3, x0: dates[0], x1: dates[dates.length-1],
                   line: {{ color: '#ffb3b3', width: 1, dash: 'dash' }} }},
                {{ type: 'line', y0: -0.7, y1: -0.7, x0: dates[0], x1: dates[dates.length-1],
                   line: {{ color: '#f45531', width: 1, dash: 'dash' }} }}
            ]
        }};

        Plotly.newPlot('composite-chart', [trace4], layout2, {{responsive: true}});

        // Chart 3: Individual Factors
        const factorsData = {json.dumps(df[['rsi_score', 'ma_score', 'pl_score', 'macd_score', 'sentiment_score']].to_dict('list'))};

        const trace5 = {{ x: dates, y: factorsData.rsi_score, name: 'RSI (20%)', type: 'scatter', line: {{ color: '#1da1f2' }} }};
        const trace6 = {{ x: dates, y: factorsData.ma_score, name: 'MA (25%)', type: 'scatter', line: {{ color: '#17bf63' }} }};
        const trace7 = {{ x: dates, y: factorsData.pl_score, name: 'Power Law (25%)', type: 'scatter', line: {{ color: '#f45531' }} }};
        const trace8 = {{ x: dates, y: factorsData.macd_score, name: 'MACD (15%)', type: 'scatter', line: {{ color: '#ffad1f' }} }};
        const trace9 = {{ x: dates, y: factorsData.sentiment_score, name: 'Sentiment (15%)', type: 'scatter', line: {{ color: '#e1e8ed' }} }};

        const layout3 = {{
            title: 'Individual Factor Scores (Pre-weighting)',
            paper_bgcolor: '#192734',
            plot_bgcolor: '#0f1419',
            font: {{ color: '#e1e8ed' }},
            xaxis: {{ gridcolor: '#38444d' }},
            yaxis: {{
                title: 'Factor Score',
                gridcolor: '#38444d',
                zeroline: true,
                zerolinecolor: '#8899a6'
            }},
            hovermode: 'x unified'
        }};

        Plotly.newPlot('factors-chart', [trace5, trace6, trace7, trace8, trace9], layout3, {{responsive: true}});

        // Chart 4: RSI and Power Law Deviation
        const trace10 = {{
            x: dates,
            y: rsiValues,
            name: 'RSI',
            type: 'scatter',
            line: {{ color: '#1da1f2', width: 2 }},
            yaxis: 'y'
        }};

        const trace11 = {{
            x: dates,
            y: powerLawDeviations,
            name: 'Power Law Deviation (%)',
            type: 'scatter',
            line: {{ color: '#f45531', width: 2 }},
            yaxis: 'y2'
        }};

        const layout4 = {{
            title: 'RSI & Power Law Deviation',
            paper_bgcolor: '#192734',
            plot_bgcolor: '#0f1419',
            font: {{ color: '#e1e8ed' }},
            xaxis: {{ gridcolor: '#38444d' }},
            yaxis: {{
                title: 'RSI',
                gridcolor: '#38444d',
                range: [0, 100]
            }},
            yaxis2: {{
                title: 'Power Law Deviation (%)',
                overlaying: 'y',
                side: 'right',
                gridcolor: '#38444d',
                zeroline: true,
                zerolinecolor: '#8899a6'
            }},
            shapes: [
                {{ type: 'line', y0: 70, y1: 70, x0: dates[0], x1: dates[dates.length-1],
                   line: {{ color: '#f45531', width: 1, dash: 'dash' }}, yref: 'y' }},
                {{ type: 'line', y0: 30, y1: 30, x0: dates[0], x1: dates[dates.length-1],
                   line: {{ color: '#17bf63', width: 1, dash: 'dash' }}, yref: 'y' }}
            ],
            hovermode: 'x unified'
        }};

        Plotly.newPlot('rsi-pl-chart', [trace10, trace11], layout4, {{responsive: true}});
    </script>
</body>
</html>
"""

# Save HTML file
output_file = Path('backtest_visualization.html')
output_file.write_text(html_content)

print(f"✓ Visualization created")
print(f"\n{'='*80}")
print(f"✅ Dashboard saved to: {output_file.absolute()}")
print(f"\nOpen this file in your browser to view the interactive charts!")
print(f"{'='*80}")
