"""
Crypto Chart Visualization Tools

Generate professional candlestick charts with technical indicators
for cryptocurrency analysis.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
from typing import Annotated, List, Optional
from datetime import datetime
import json


class CryptoChartGenerator:
    """Generate cryptocurrency charts with technical indicators."""
    
    def __init__(self):
        self.coingecko_base = "https://api.coingecko.com/api/v3"
    
    def fetch_ohlc_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Fetch OHLC (Open, High, Low, Close) data from CoinGecko."""
        try:
            url = f"{self.coingecko_base}/coins/{symbol.lower()}/ohlc"
            params = {
                'vs_currency': 'usd',
                'days': days
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Convert to DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('date')
            
            return df
            
        except Exception as e:
            raise Exception(f"Error fetching OHLC data: {str(e)}")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for the dataframe."""
        # Simple Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # Exponential Moving Averages
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volume analysis (if available)
        if 'volume' in df.columns:
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def create_candlestick_chart(
        self,
        symbol: Annotated[str, "The cryptocurrency symbol (e.g., 'bitcoin', 'ethereum')"],
        days: Annotated[int, "Number of days to chart (7-365)"] = 30,
        indicators: Annotated[List[str], "List of indicators to include: 'sma', 'ema', 'bb', 'rsi', 'macd'"] = None,
        output_file: Annotated[str, "Output file path for the chart"] = None,
    ) -> str:
        """
        Generate a candlestick chart with technical indicators.
        
        Args:
            symbol: Cryptocurrency symbol
            days: Number of days to chart
            indicators: List of indicators to include
            output_file: Path to save the chart
            
        Returns:
            Status message with chart information
        """
        try:
            if indicators is None:
                indicators = ['sma', 'rsi', 'macd']
            
            # Fetch data
            df = self.fetch_ohlc_data(symbol, days)
            df = self.calculate_indicators(df)
            
            # Determine number of subplots needed
            num_subplots = 1
            if 'rsi' in indicators:
                num_subplots += 1
            if 'macd' in indicators:
                num_subplots += 1
            
            # Create subplot layout
            row_heights = [0.6] + [0.2] * (num_subplots - 1)
            subplot_titles = [f'{symbol.upper()} Price Chart']
            
            if 'rsi' in indicators:
                subplot_titles.append('RSI (14)')
            if 'macd' in indicators:
                subplot_titles.append('MACD')
            
            fig = make_subplots(
                rows=num_subplots,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=row_heights,
                subplot_titles=subplot_titles
            )
            
            # Main candlestick chart
            fig.add_trace(
                go.Candlestick(
                    x=df['date'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='Price',
                    increasing_line_color='#26a69a',
                    decreasing_line_color='#ef5350'
                ),
                row=1, col=1
            )
            
            # Add Moving Averages
            if 'sma' in indicators:
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['sma_20'],
                        name='SMA 20',
                        line=dict(color='orange', width=1.5)
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['sma_50'],
                        name='SMA 50',
                        line=dict(color='blue', width=1.5)
                    ),
                    row=1, col=1
                )
            
            if 'ema' in indicators:
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['ema_12'],
                        name='EMA 12',
                        line=dict(color='purple', width=1, dash='dash')
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['ema_26'],
                        name='EMA 26',
                        line=dict(color='pink', width=1, dash='dash')
                    ),
                    row=1, col=1
                )
            
            # Add Bollinger Bands
            if 'bb' in indicators:
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['bb_upper'],
                        name='BB Upper',
                        line=dict(color='gray', width=1, dash='dot'),
                        opacity=0.5
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['bb_lower'],
                        name='BB Lower',
                        line=dict(color='gray', width=1, dash='dot'),
                        fill='tonexty',
                        fillcolor='rgba(128, 128, 128, 0.1)',
                        opacity=0.5
                    ),
                    row=1, col=1
                )
            
            # Add RSI
            current_row = 2
            if 'rsi' in indicators:
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['rsi'],
                        name='RSI',
                        line=dict(color='purple', width=2)
                    ),
                    row=current_row, col=1
                )
                # Add RSI levels
                fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=current_row, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=current_row, col=1)
                fig.update_yaxes(range=[0, 100], row=current_row, col=1)
                current_row += 1
            
            # Add MACD
            if 'macd' in indicators:
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['macd'],
                        name='MACD',
                        line=dict(color='blue', width=2)
                    ),
                    row=current_row, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['macd_signal'],
                        name='Signal',
                        line=dict(color='orange', width=2)
                    ),
                    row=current_row, col=1
                )
                fig.add_trace(
                    go.Bar(
                        x=df['date'],
                        y=df['macd_histogram'],
                        name='Histogram',
                        marker_color='lightblue'
                    ),
                    row=current_row, col=1
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=current_row, col=1)
            
            # Update layout
            fig.update_layout(
                title=f'{symbol.upper()} Technical Analysis',
                xaxis_title='Date',
                yaxis_title='Price (USD)',
                template='plotly_dark',
                height=300 * num_subplots,
                hovermode='x unified',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            # Remove rangeslider
            fig.update_xaxes(rangeslider_visible=False)
            
            # Save chart
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"outputs/{symbol}_chart_{timestamp}.html"
            
            fig.write_html(output_file)
            
            # Generate analysis summary
            latest = df.iloc[-1]
            analysis = {
                'symbol': symbol.upper(),
                'chart_file': output_file,
                'period': f'{days} days',
                'latest_data': {
                    'date': str(latest['date']),
                    'close': latest['close'],
                    'sma_20': latest['sma_20'] if pd.notna(latest['sma_20']) else None,
                    'rsi': latest['rsi'] if pd.notna(latest['rsi']) else None,
                    'macd': latest['macd'] if pd.notna(latest['macd']) else None,
                },
                'signals': []
            }
            
            # Generate signals
            if pd.notna(latest['rsi']):
                if latest['rsi'] < 30:
                    analysis['signals'].append('RSI indicates OVERSOLD (< 30)')
                elif latest['rsi'] > 70:
                    analysis['signals'].append('RSI indicates OVERBOUGHT (> 70)')
            
            if pd.notna(latest['close']) and pd.notna(latest['sma_20']):
                if latest['close'] > latest['sma_20']:
                    analysis['signals'].append('Price above SMA20 (Bullish)')
                else:
                    analysis['signals'].append('Price below SMA20 (Bearish)')
            
            if pd.notna(latest['macd']) and pd.notna(latest['macd_signal']):
                if latest['macd'] > latest['macd_signal']:
                    analysis['signals'].append('MACD above signal line (Bullish)')
                else:
                    analysis['signals'].append('MACD below signal line (Bearish)')
            
            return json.dumps(analysis, indent=2)
            
        except Exception as e:
            return f"Error generating chart: {str(e)}"


# Create singleton instance
chart_generator = CryptoChartGenerator()

def create_crypto_chart(
    symbol: str,
    days: int = 30,
    indicators: List[str] = None,
    output_file: str = None
) -> str:
    """Generate a cryptocurrency chart with technical indicators."""
    return chart_generator.create_candlestick_chart(symbol, days, indicators, output_file)
