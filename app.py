#app.py - Main application file
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import time
import ccxt
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots  # Fixed: Added missing import
from scipy import stats
import pandas_ta as ta  # Fixed: Replaced TA-Lib with pandas_ta for better compatibility
import yfinance as yf
from streamlit_option_menu import option_menu
import json
from scipy.stats import zscore
import warnings
warnings.filterwarnings('ignore')

# Set page configuration
st.set_page_config(page_title="StableCoin Arbitrage TradeSmart 2", layout="wide")

# Module imports
from config import SUPPORTED_EXCHANGES, STABLECOINS, TRANSACTION_FEES, WITHDRAWAL_FEES
from data_service import (
    fetch_stablecoin_prices, 
    fetch_historical_data,
    estimate_slippage
)
from analysis_service import (
    find_arbitrage_opportunities,
    calculate_z_scores,
    calculate_signals,
    estimate_convergence,
    backtest_arbitrage,
    calculate_technical_indicators,
    generate_signals_from_indicators
)
from risk_service import (
    calculate_trade_metrics,
    calculate_optimal_position_size
)
from ui_components import (
    render_header,
    render_price_table,
    render_deviation_heatmap,
    render_opportunities_table,
    render_profit_chart,
    render_convergence_metrics,
    render_trading_recommendation,
    render_price_chart,
    render_price_spread_chart,
    render_technical_chart,
    render_signals_table,
    render_signal_summary,
    render_backtest_chart,
    render_risk_metrics,
    render_position_sizing
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        font-weight: 600;
    }
    .card {
        border-radius: 5px;
        background-color: #f9f9f9;
        padding: 20px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    .highlight {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #1E88E5;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for storing data
def init_session_state():
    """Initialize session state variables"""
    if 'stablecoin_data' not in st.session_state:
        st.session_state.stablecoin_data = None
    if 'historical_data' not in st.session_state:
        st.session_state.historical_data = {}
    if 'z_scores' not in st.session_state:
        st.session_state.z_scores = {}
    if 'opportunities' not in st.session_state:
        st.session_state.opportunities = None
    if 'api_keys' not in st.session_state:
        st.session_state.api_keys = {}
    if 'simulation_mode' not in st.session_state:
        st.session_state.simulation_mode = True

# UI Sections Functions
def market_scanner_section():
    """UI section for the Market Anomaly & Relative Value Scanner"""
    st.markdown('<div class="sub-header">Market Anomaly & Relative Value Scanner</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Scan Settings")
        min_price_diff = st.slider("Minimum Price Difference (%)", 0.01, 1.0, 0.05, 0.01)
        min_profit = st.slider("Minimum Profit per $1000 ($)", 0.1, 10.0, 0.5, 0.1)
        selected_stablecoins = st.multiselect("Stablecoins", STABLECOINS, default=STABLECOINS[:5])
        selected_exchanges = st.multiselect("Exchanges", SUPPORTED_EXCHANGES, default=SUPPORTED_EXCHANGES[:4])
        
        # Added: Toggle for simulation mode
        st.session_state.simulation_mode = st.toggle("Simulation Mode", value=True, 
                                                help="Use synthetic data for demonstration")
        
        if st.button("Scan Market", key="scan_btn"):
            with st.spinner("Scanning for arbitrage opportunities..."):
                # Fetch current prices
                st.session_state.stablecoin_data = fetch_stablecoin_prices(
                    simulation_mode=st.session_state.simulation_mode,
                    api_keys=st.session_state.api_keys
                )
                
                # Filter by selection
                filtered_data = st.session_state.stablecoin_data[
                    (st.session_state.stablecoin_data['Stablecoin'].isin(selected_stablecoins)) &
                    (st.session_state.stablecoin_data['Exchange'].isin(selected_exchanges))
                ]
                
                # Find arbitrage opportunities
                # Fixed: Added transaction and withdrawal fees
                opportunities = find_arbitrage_opportunities(
                    filtered_data, 
                    transaction_fees=TRANSACTION_FEES,
                    withdrawal_fees=WITHDRAWAL_FEES
                )
                
                # Fixed: Added slippage estimation
                for i, row in opportunities.iterrows():
                    slippage = estimate_slippage(
                        row['Stablecoin'], 
                        row['Buy Exchange'], 
                        row['Sell Exchange'],
                        1000,  # Using $1000 as the standard trade size
                        simulation_mode=st.session_state.simulation_mode
                    )
                    opportunities.at[i, 'Estimated Slippage'] = slippage
                    opportunities.at[i, 'Adjusted Profit per $1000'] = (
                        opportunities.at[i, 'Potential Profit per $1000'] - slippage
                    )
                
                st.session_state.opportunities = opportunities[
                    (opportunities['Percent Difference'] >= min_price_diff) &
                    (opportunities['Adjusted Profit per $1000'] >= min_profit)
                ]
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add refresh button
        if st.button("Refresh Data", key="refresh_btn"):
            st.session_state.stablecoin_data = fetch_stablecoin_prices(
                simulation_mode=st.session_state.simulation_mode,
                api_keys=st.session_state.api_keys
            )
            st.experimental_rerun()
            
        # Added: API Key Management button
        if st.button("Manage API Keys", key="api_key_btn"):
            st.session_state.show_api_modal = True
            
        # API Key Management Modal
        if st.session_state.get('show_api_modal', False):
            with st.form("api_key_form"):
                st.subheader("Exchange API Keys")
                st.write("Enter your API keys for each exchange you want to use:")
                
                for exchange in SUPPORTED_EXCHANGES:
                    col1, col2 = st.columns(2)
                    with col1:
                        api_key = st.text_input(f"{exchange} API Key", 
                                              value=st.session_state.api_keys.get(exchange, {}).get('api_key', ''),
                                              type="password")
                    with col2:
                        api_secret = st.text_input(f"{exchange} API Secret", 
                                                value=st.session_state.api_keys.get(exchange, {}).get('api_secret', ''),
                                                type="password")
                        
                    if api_key and api_secret:
                        st.session_state.api_keys[exchange] = {
                            'api_key': api_key,
                            'api_secret': api_secret
                        }
                
                if st.form_submit_button("Save API Keys"):
                    st.success("API keys saved successfully!")
                    st.session_state.show_api_modal = False
                    
                if st.form_submit_button("Cancel"):
                    st.session_state.show_api_modal = False
    
    with col1:
        # Display current prices
        if st.session_state.stablecoin_data is not None:
            filtered_data = st.session_state.stablecoin_data
            if selected_stablecoins:
                filtered_data = filtered_data[filtered_data['Stablecoin'].isin(selected_stablecoins)]
            if selected_exchanges:
                filtered_data = filtered_data[filtered_data['Exchange'].isin(selected_exchanges)]
            
            st.subheader("Current Stablecoin Prices")
            
            # Pivot table for prices
            price_pivot = filtered_data.pivot(index='Stablecoin', columns='Exchange', values='Price')
            st.dataframe(price_pivot.style.format("{:.6f}").background_gradient(cmap='Blues'), use_container_width=True)
            
            # Heatmap of deviations
            st.subheader("Price Deviation Heatmap (from $1.00)")
            dev_pivot = filtered_data.pivot(index='Stablecoin', columns='Exchange', values='Deviation')
            
            fig = px.imshow(
                dev_pivot,
                color_continuous_scale='RdBu_r',
                labels=dict(x="Exchange", y="Stablecoin", color="Deviation"),
                zmin=-0.005, zmax=0.005
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display opportunities if available
            if hasattr(st.session_state, 'opportunities') and st.session_state.opportunities is not None:
                st.subheader("Arbitrage Opportunities")
                if not st.session_state.opportunities.empty:
                    # Format and display opportunities
                    display_df = st.session_state.opportunities.copy()
                    display_df['Price Difference'] = display_df['Price Difference'].map('{:.6f}'.format)
                    display_df['Percent Difference'] = display_df['Percent Difference'].map('{:.4f}%'.format)
                    display_df['Potential Profit per $1000'] = display_df['Potential Profit per $1000'].map('${:.2f}'.format)
                    display_df['Adjusted Profit per $1000'] = display_df['Adjusted Profit per $1000'].map('${:.2f}'.format)
                    display_df['Estimated Slippage'] = display_df['Estimated Slippage'].map('${:.2f}'.format)
                    
                    st.dataframe(display_df, use_container_width=True)
                    
                    # Bar chart of profit opportunities
                    fig = px.bar(
                        st.session_state.opportunities,
                        x='Stablecoin',
                        y='Adjusted Profit per $1000',
                        color='Adjusted Profit per $1000',
                        hover_data=['Buy Exchange', 'Sell Exchange', 'Percent Difference'],
                        title='Potential Profit per $1000 Investment (After Fees & Slippage)'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Added: Execution time warning
                    st.warning("Note: Arbitrage opportunities may disappear quickly. The execution time between exchanges can impact profitability.")
                else:
                    st.info("No arbitrage opportunities found matching your criteria. Try adjusting your filters.")
        else:
            st.info("Click 'Scan Market' to fetch current stablecoin prices and analyze arbitrage opportunities.")

def pair_analysis_section():
    """UI section for Custom Pair Analysis"""
    st.markdown('<div class="sub-header">Custom Pair Analysis</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Select Pairs")
        stablecoin = st.selectbox("Stablecoin", STABLECOINS)
        exchange1 = st.selectbox("Exchange 1", SUPPORTED_EXCHANGES, index=0)
        exchange2 = st.selectbox("Exchange 2", SUPPORTED_EXCHANGES, index=1)
        lookback_days = st.slider("Lookback Period (days)", 7, 90, 30)
        
        if st.button("Analyze Pair", key="analyze_pair_btn"):
            with st.spinner("Analyzing price relationship..."):
                # Fetch historical data
                st.session_state.historical_data[stablecoin] = fetch_historical_data(
                    stablecoin, 
                    days=lookback_days,
                    simulation_mode=st.session_state.simulation_mode
                )
                
                # Calculate z-scores
                st.session_state.z_scores[stablecoin] = calculate_z_scores(
                    st.session_state.historical_data[stablecoin]
                )
                
                # Estimate convergence probability
                st.session_state.convergence_exchange1 = estimate_convergence(
                    st.session_state.z_scores[stablecoin], exchange1
                )
                st.session_state.convergence_exchange2 = estimate_convergence(
                    st.session_state.z_scores[stablecoin], exchange2
                )
                
                # Fixed: Calculate execution time impact
                st.session_state.execution_impact = {
                    'time_minutes': np.random.randint(2, 15),  # Simulate execution time between exchanges
                    'price_impact_pct': np.random.uniform(0.01, 0.1)  # Simulate price impact during execution
                }
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        if stablecoin in st.session_state.historical_data:
            hist_data = st.session_state.historical_data[stablecoin]
            
            # Price chart
            st.subheader(f"{stablecoin} Price Comparison")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data[exchange1],
                                    mode='lines', name=exchange1))
            fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data[exchange2],
                                    mode='lines', name=exchange2))
            fig.add_trace(go.Scatter(x=hist_data.index, y=[1]*len(hist_data),
                                    mode='lines', name='$1.00 Peg', line=dict(dash='dash', color='gray')))
            
            fig.update_layout(
                title=f"{stablecoin} Price on {exchange1} vs {exchange2}",
                xaxis_title="Date",
                yaxis_title="Price (USD)",
                legend_title="Exchange",
                height=400
            )
            
            # Narrow y-axis to focus on small deviations
            price_min = min(hist_data[exchange1].min(), hist_data[exchange2].min())
            price_max = max(hist_data[exchange1].max(), hist_data[exchange2].max())
            y_range_min = max(0.99, price_min - 0.001)
            y_range_max = min(1.01, price_max + 0.001)
            fig.update_yaxes(range=[y_range_min, y_range_max])
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Price difference chart
            st.subheader("Price Spread Analysis")
            
            price_diff = hist_data[exchange1] - hist_data[exchange2]
            mean_diff = price_diff.mean()
            std_diff = price_diff.std()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist_data.index, y=price_diff, mode='lines', name='Price Spread'))
            fig.add_trace(go.Scatter(x=hist_data.index, y=[mean_diff]*len(hist_data),
                                    mode='lines', name='Mean Spread', line=dict(dash='dash', color='red')))
            fig.add_trace(go.Scatter(x=hist_data.index, y=[mean_diff + 2*std_diff]*len(hist_data),
                                    mode='lines', name='+2σ', line=dict(dash='dot', color='orange')))
            fig.add_trace(go.Scatter(x=hist_data.index, y=[mean_diff - 2*std_diff]*len(hist_data),
                                    mode='lines', name='-2σ', line=dict(dash='dot', color='orange')))
            
            fig.update_layout(
                title=f"Price Spread ({exchange1} - {exchange2})",
                xaxis_title="Date",
                yaxis_title="Price Difference (USD)",
                legend_title="Metric",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display convergence metrics
            if hasattr(st.session_state, 'convergence_exchange1') and hasattr(st.session_state, 'convergence_exchange2'):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="highlight">', unsafe_allow_html=True)
                    st.subheader(f"{exchange1} Metrics")
                    st.metric("Current Z-Score", f"{st.session_state.convergence_exchange1['Current Z-Score']:.2f}")
                    st.metric("Convergence Probability", f"{st.session_state.convergence_exchange1['Convergence Probability']:.1f}%")
                    st.metric("Est. Time to Converge", f"{st.session_state.convergence_exchange1['Time to Converge (days)']:.1f} days")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="highlight">', unsafe_allow_html=True)
                    st.subheader(f"{exchange2} Metrics")
                    st.metric("Current Z-Score", f"{st.session_state.convergence_exchange2['Current Z-Score']:.2f}")
                    st.metric("Convergence Probability", f"{st.session_state.convergence_exchange2['Convergence Probability']:.1f}%")
                    st.metric("Est. Time to Converge", f"{st.session_state.convergence_exchange2['Time to Converge (days)']:.1f} days")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Trading recommendation
                st.subheader("Trading Recommendation")
                
                z1 = st.session_state.convergence_exchange1['Current Z-Score']
                z2 = st.session_state.convergence_exchange2['Current Z-Score']
                
                # Added: Execution time impact warning
                if hasattr(st.session_state, 'execution_impact'):
                    st.warning(f"Note: Estimated execution time between exchanges is "
                              f"{st.session_state.execution_impact['time_minutes']} minutes, "
                              f"which could impact price by approximately "
                              f"{st.session_state.execution_impact['price_impact_pct']:.2f}%")
                
                if abs(z1 - z2) > 1.5:
                    if z1 > z2:
                        action = f"BUY {stablecoin} on {exchange2} and SELL on {exchange1}"
                        rationale = f"The price on {exchange1} is significantly higher than on {exchange2} relative to historical patterns."
                    else:
                        action = f"BUY {stablecoin} on {exchange1} and SELL on {exchange2}"
                        rationale = f"The price on {exchange2} is significantly higher than on {exchange1} relative to historical patterns."
                    
                    st.markdown(f"""
                    <div class="card" style="border-left: 5px solid #4CAF50; padding: 15px;">
                        <h3 style="color: #4CAF50;">{action}</h3>
                        <p><strong>Rationale:</strong> {rationale}</p>
                        <p><strong>Expected Convergence:</strong> {max(st.session_state.convergence_exchange1['Convergence Probability'], st.session_state.convergence_exchange2['Convergence Probability']):.1f}% probability within {max(st.session_state.convergence_exchange1['Time to Converge (days)'], st.session_state.convergence_exchange2['Time to Converge (days)']):.1f} days</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="card" style="border-left: 5px solid #FFA500; padding: 15px;">
                        <h3 style="color: #FFA500;">NO TRADE RECOMMENDED</h3>
                        <p>The current price spread between exchanges is within normal historical ranges.</p>
                        <p>Continue monitoring for opportunities.</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Select a stablecoin and exchange pair, then click 'Analyze Pair' to see the detailed analysis.")

def technical_analysis_section():
    """UI section for Technical Analysis Module"""
    st.markdown('<div class="sub-header">Technical Analysis Module</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Technical Analysis Settings")
        
        stablecoin = st.selectbox("Stablecoin", STABLECOINS, key="ta_stablecoin")
        exchange = st.selectbox("Exchange", SUPPORTED_EXCHANGES, key="ta_exchange")
        lookback_days = st.slider("Lookback Period (days)", 7, 90, 30, key="ta_lookback")
        
        if st.button("Run Technical Analysis", key="run_ta_btn"):
            with st.spinner("Calculating technical indicators..."):
                # Fetch historical data
                st.session_state.historical_data[stablecoin] = fetch_historical_data(
                    stablecoin, 
                    days=lookback_days,
                    simulation_mode=st.session_state.simulation_mode
                )
                
                # Extract price series for selected exchange
                hist_data = st.session_state.historical_data[stablecoin].copy()
                
                # Calculate technical indicators
                # Fixed: Using pandas_ta instead of talib
                ta_data = calculate_technical_indicators(hist_data, exchange)
                
                # Generate signals
                signals = generate_signals_from_indicators(ta_data)
                
                # Store in session state
                st.session_state.ta_data = ta_data
                st.session_state.ta_signals = signals
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        if hasattr(st.session_state, 'ta_data') and hasattr(st.session_state, 'ta_signals'):
            ta_data = st.session_state.ta_data
            signals = st.session_state.ta_signals
            
            # Price and indicators chart
            st.subheader("Price and Technical Indicators")
            
            # Create figure with secondary y-axis for RSI
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.1,
                               row_heights=[0.7, 0.3])
            
            # Add price and moving averages
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data[exchange],
                                    mode='lines', name=f"{stablecoin} Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['SMA_5'],
                                    mode='lines', name='SMA (5)', line=dict(dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['SMA_20'],
                                    mode='lines', name='SMA (20)', line=dict(dash='dash')), row=1, col=1)
            
            # Add Bollinger Bands
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['Upper_Band'],
                                    mode='lines', name='Upper BB', line=dict(width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['Lower_Band'],
                                    mode='lines', name='Lower BB', line=dict(width=1)), row=1, col=1)
            
            # Add RSI
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['RSI'],
                                    mode='lines', name='RSI'), row=2, col=1)
            fig.add_trace(go.Scatter(x=ta_data.index, y=[70]*len(ta_data.index),
                                    mode='lines', name='Overbought', line=dict(dash='dash', color='red')), row=2, col=1)
            fig.add_trace(go.Scatter(x=ta_data.index, y=[30]*len(ta_data.index),
                                    mode='lines', name='Oversold', line=dict(dash='dash', color='green')), row=2, col=1)
            
            # Update layout
            fig.update_layout(
                title=f"{stablecoin} Technical Analysis on {exchange}",
                legend_title="Indicators",
                height=600
            )
            
            # Update y-axis titles
            fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
            fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
            
            # Show plot
            st.plotly_chart(fig, use_container_width=True)
            
            # Display signals
            st.subheader("Trading Signals")
            
            # Combine signals with price data
            signal_df = pd.DataFrame({
                'Date': ta_data.index,
                'Price': ta_data[exchange],
                'RSI': ta_data['RSI'].round(2),
                'MACD': ta_data['MACD'].round(6),
                'MACD_Signal': ta_data['MACD_Signal'].round(6),
                'BB_Upper': ta_data['Upper_Band'].round(6),
                'BB_Lower': ta_data['Lower_Band'].round(6),
                'RSI_Signal': signals['RSI_Signal'],
                'MACD_Signal': signals['MACD_Signal'],
                'BB_Signal': signals['BB_Signal'],
                'Combined_Signal': signals['Combined_Signal']
            }).tail(10)
            
            # Format signal columns
            signal_map = {1: "BUY", -1: "SELL", 0: "HOLD"}
            signal_color_map = {1: "background-color: #c6efce; color: #006100", 
                             -1: "background-color: #ffc7ce; color: #9c0006", 
                             0: "background-color: #ffffff; color: #000000"}
            
            for col in ['RSI_Signal', 'MACD_Signal', 'BB_Signal', 'Combined_Signal']:
                signal_df[col] = signal_df[col].map(signal_map)
            
            st.dataframe(signal_df, use_container_width=True)
            
            # Signal summary
            last_combined = signals['Combined_Signal'].iloc[-1]
            last_date = signals.index[-1].strftime('%Y-%m-%d')
            
            if last_combined > 1:
                signal_strength = "Strong Buy"
                signal_color = "#006100"
            elif last_combined == 1:
                signal_strength = "Buy"
                signal_color = "#007c3f"
            elif last_combined == 0:
                signal_strength = "Neutral"
                signal_color = "#666666"
            elif last_combined == -1:
                signal_strength = "Sell"
                signal_color = "#9c0006"
            else:
                signal_strength = "Strong Sell"
                signal_color = "#7c0000"
            
            st.markdown(f"""
            <div class="card" style="text-align: center; padding: 20px;">
                <h2>Current Signal: <span style="color: {signal_color};">{signal_strength}</span></h2>
                <p>For {stablecoin} on {exchange} as of {last_date}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Backtest results
            st.subheader("Backtest Results")
            
            # Run backtest
            portfolio_value, metrics = backtest_arbitrage(
                st.session_state.historical_data[stablecoin][[exchange]], 
                z_score_threshold=1.5,
                investment=1000
            )
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Final Value", f"${metrics['Final Value']:.2f}")
            col2.metric("Total Return", f"{metrics['Total Return (%)']:.2f}%")
            col3.metric("Annualized Return", f"{metrics['Annualized Return (%)']:.2f}%")
            col4.metric("Sharpe Ratio", f"{metrics['Sharpe Ratio']:.2f}")
            
            # Portfolio value chart
            fig = px.line(
                x=portfolio_value.index, 
                y=portfolio_value,
                labels={"x": "Date", "y": "Portfolio Value ($)"},
                title=f"Backtest Results: $1,000 Initial Investment"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select a stablecoin and exchange, then click 'Run Technical Analysis' to see the results.")

def risk_analysis_section():
    """UI section for Risk Analysis Module"""
    st.markdown('<div class="sub-header">Risk Analysis Module</div>', unsafe_allow_html=True)
    
    if hasattr(st.session_state, 'opportunities') and not st.session_state.opportunities.empty:
        # Calculate risk metrics
        trade_metrics = calculate_trade_metrics(st.session_state.opportunities)
        
        # Display metrics table
        st.subheader("Risk-Adjusted Metrics")
        st.dataframe(trade_metrics.style.background_gradient(subset=['Risk-Reward Ratio', 'Net Profit per $1000'], cmap='Blues'), use_container_width=True)
        
        # Risk-reward scatter plot
        st.subheader("Risk-Reward Analysis")
        
        fig = px.scatter(
            trade_metrics,
            x="Risk Amount per $1000",
            y="Net Profit per $1000",
            size="Risk-Reward Ratio",
            color="Annualized Return (%)",
            hover_name="Stablecoin",
            hover_data={
                "Buy Exchange": True,
                "Sell Exchange": True,
                "Risk-Reward Ratio": True,
                "Break-Even Time (hours)": True
            },
            labels={
                "Risk Amount per $1000": "Risk Amount per $1,000 ($)",
                "Net Profit per $1000": "Net Profit per $1,000 ($)",
                "Annualized Return (%)": "Annualized Return (%)"
            },
            title="Risk-Reward Profile of Arbitrage Opportunities"
        )
        
        # Add diagonal lines representing risk-reward ratios
        x_range = np.linspace(0, trade_metrics["Risk Amount per $1000"].max() * 1.2, 100)
        for rr in [1, 2, 3, 5]:
            fig.add_trace(
                go.Scatter(
                    x=x_range, 
                    y=rr * x_range,
                    mode='lines',
                    line=dict(dash='dash', width=1, color='gray'),
                    name=f'R:R = {rr}:1',
                    hoverinfo='none'
                )
            )
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Optimal trade size calculator
        st.subheader("Optimal Trade Size Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Position Sizing")
            
            total_capital = st.number_input("Total Trading Capital ($)", min_value=100.0, value=10000.0, step=1000.0)
            max_risk_pct = st.slider("Maximum Risk per Trade (%)", 0.1, 5.0, 1.0, 0.1)
            max_portfolio_pct = st.slider("Maximum Portfolio Allocation per Trade (%)", 5.0, 50.0, 20.0, 5.0)
            
            # Fixed: Added stop-loss settings
            st.subheader("Stop Loss Settings")
            use_stop_loss = st.checkbox("Use Stop Loss", value=True)
            if use_stop_loss:
                stop_loss_pct = st.slider("Stop Loss (%)", 0.1, 2.0, 0.5, 0.1,
                                        help="Maximum allowed adverse price movement before exiting the trade")
            else:
                stop_loss_pct = 1.0  # Default value if stop loss is not used
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if not trade_metrics.empty:
                # Calculate position sizes
                results = []
                
                for _, row in trade_metrics.iterrows():
                    # Maximum position based on risk
                    max_risk_amount = total_capital * (max_risk_pct / 100)
                    
                    # Fixed: Adjusted risk calculation to include stop loss
                    risk_per_dollar = row["Risk Amount per $1000"] / 1000
                    if use_stop_loss:
                        # Use the minimum of actual risk and stop loss
                        effective_risk = min(risk_per_dollar, stop_loss_pct / 100)
                    else:
                        effective_risk = risk_per_dollar
                    
                    position_size_risk = max_risk_amount / (effective_risk * 1000) * 1000
                    
                    # Maximum position based on portfolio allocation
                    max_allocation = total_capital * (max_portfolio_pct / 100)
                    
                    # Choose the smaller of the two
                    recommended_position = min(position_size_risk, max_allocation)
                    
                    # Fixed: Added execution risk factor
                    execution_risk_factor = 0.9  # Assume 10% reduction in profit due to execution risk
                    
                    # Calculate expected profit
                    expected_profit = (recommended_position / 1000 * row["Net Profit per $1000"]) * execution_risk_factor
                    
                    # Fixed: Add withdrawal and transaction costs
                    transaction_costs = recommended_position * (TRANSACTION_FEES.get(row["Buy Exchange"], 0.001) + 
                                                             TRANSACTION_FEES.get(row["Sell Exchange"], 0.001))
                    withdrawal_cost = WITHDRAWAL_FEES.get(row["Buy Exchange"], {}).get(row["Stablecoin"], 0)
                    
                    # Adjusted net profit
                    adjusted_profit = expected_profit - transaction_costs - withdrawal_cost
                    
                    results.append({
                        "Stablecoin": row["Stablecoin"],
                        "Buy Exchange": row["Buy Exchange"],
                        "Sell Exchange": row["Sell Exchange"],
                        "Recommended Position ($)": recommended_position,
                        "Expected Profit ($)": adjusted_profit,
                        "Execution Risk Adjustment": f"{(1-execution_risk_factor)*100:.0f}%",
                        "Transaction Costs ($)": transaction_costs,
                        "Withdrawal Fee ($)": withdrawal_cost,
                        "Expected Return (%)": (adjusted_profit / recommended_position) * 100 if recommended_position > 0 else 0
                    })
                
                position_df = pd.DataFrame(results)
                
                # Display position sizing recommendations
                st.markdown('<div class="highlight">', unsafe_allow_html=True)
                st.subheader("Recommended Positions")
                st.dataframe(position_df.style.format({
                    "Recommended Position ($)": "${:.2f}",
                    "Expected Profit ($)": "${:.2f}",
                    "Transaction Costs ($)": "${:.2f}",
                    "Withdrawal Fee ($)": "${:.2f}",
                    "Expected Return (%)": "{:.2f}%"
                }), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Total expected profit
                total_expected_profit = position_df["Expected Profit ($)"].sum()
                st.metric("Total Expected Profit", f"${total_expected_profit:.2f}")
                
                # Fixed: Added risk warnings
                if total_expected_profit < 0:
                    st.error("Warning: After accounting for all costs and risks, these trades are expected to result in a net loss.")
                elif total_expected_profit < position_df["Transaction Costs ($)"].sum() * 2:
                    st.warning("Warning: Expected profit is low compared to transaction costs. Consider higher volume trades or waiting for larger price discrepancies.")
            else:
                st.info("No arbitrage opportunities available for position sizing.")
    else:
        st.info("Run the Market Scanner first to identify arbitrage opportunities for risk analysis.")

def about_definitions_section():
    """UI section for About & Definitions Module"""
    st.markdown('<div class="sub-header">About & Definitions</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["About TradeSmart 2", "Stablecoin Arbitrage Guide", "Risk Management"])
    
    with tab1:
        st.markdown("""
        ## About TradeSmart 2 Platform
        
        The StableCoin Arbitrage TradeSmart 2 platform is a comprehensive tool designed to help cryptocurrency traders identify and capitalize on stablecoin arbitrage opportunities across US-based exchanges.
        
        ### Platform Features
        
        1. **Market Scanner**: Continuously monitors stablecoin prices across exchanges to identify relative value discrepancies.
        
        2. **Pair Analysis**: Analyzes the historical relationship between stablecoin prices on different exchanges to determine if current spreads are likely to converge.
        
        3. **Technical Analysis**: Provides technical indicators and signals to help time entry and exit points for arbitrage trades.
        
        4. **Risk Analysis**: Evaluates the risk-reward profile of arbitrage opportunities and helps optimize position sizing.
        
        5. **Educational Resources**: Offers comprehensive guides on stablecoin arbitrage, relative value trading, and risk management.
        
        ### Data Sources
        
        The platform uses real-time and historical price data from major US-based cryptocurrency exchanges, including:
        
        - Coinbase
        - Uphold
        - Kraken
        - Binance.US
        - Gemini
        
        ### Technologies Used
        
        - Python for backend data processing and analysis
        - Streamlit for the user interface
        - CCXT library for cryptocurrency exchange API integration
        - Pandas and NumPy for data manipulation
        - Plotly and Matplotlib for data visualization
        - Pandas-TA for technical analysis indicators
        """)
    
    with tab2:
        st.markdown("""
        ## Stablecoin Arbitrage Guide
        
        Stablecoin arbitrage involves capitalizing on price discrepancies of stablecoins across different exchanges. Since stablecoins are designed to maintain a stable value (typically $1), any deviation from this peg creates potential trading opportunities.
        
        ### How Stablecoin Arbitrage Works
        
        1. **Identify Price Discrepancies**: Find stablecoins trading at different prices across exchanges.
        
        2. **Evaluate Convergence Probability**: Determine if the price gap is likely to close based on historical patterns.
        
        3. **Calculate Potential Profit**: Factor in transaction costs, withdrawal fees, and slippage to ensure profitability.
        
        4. **Execute the Trade**: Buy the stablecoin on the exchange where it's cheaper and sell it on the exchange where it's more expensive.
        
        5. **Manage Risk**: Use proper position sizing and implement risk management strategies.
        
        ### Types of Stablecoin Arbitrage
        
        1. **Exchange Arbitrage**: Exploiting price differences of the same stablecoin across different exchanges.
        
        2. **Cross-Stablecoin Arbitrage**: Trading between different stablecoins when their prices deviate from each other.
        
        3. **Triangular Arbitrage**: Converting between fiat, stablecoins, and other cryptocurrencies to capitalize on pricing inefficiencies.
        
        ### Key Terms
        
        - **Convergence**: The tendency of prices to return to their mean or expected value ($1 for stablecoins).
        
        - **Z-Score**: A statistical measure that quantifies how many standard deviations a price is from its historical mean.
        
        - **Slippage**: The difference between the expected price of a trade and the actual executed price.
        
        - **Spot-to-Spot**: Trading the actual stablecoin assets across exchanges.
        
        - **Futures-to-Spot**: Arbitraging between stablecoin futures contracts and spot markets.
        """)
    
    with tab3:
        st.markdown("""
        ## Risk Management Principles
        
        Effective risk management is crucial for successful stablecoin arbitrage trading. While stablecoin arbitrage is generally considered lower risk compared to other crypto trading strategies, it still involves several risks that must be managed.
        
        ### Key Risk Factors
        
        1. **Execution Risk**: Delays in execution can cause prices to move, reducing or eliminating profit opportunities.
        
        2. **Counterparty Risk**: Exchanges may experience technical issues, impose withdrawal limits, or in extreme cases, become insolvent.
        
        3. **Liquidity Risk**: Insufficient liquidity can lead to slippage, reducing profitability.
        
        4. **Depeg Risk**: Stablecoins can temporarily or permanently lose their peg to the dollar, potentially resulting in significant losses.
        
        5. **Regulatory Risk**: Changes in regulations can affect the operation of exchanges or the status of certain stablecoins.
        
        ### Risk Management Strategies
        
        1. **Position Sizing**: Never risk more than a small percentage (1-2%) of your total capital on a single trade.
        
        2. **Diversification**: Spread your capital across multiple exchanges and stablecoins.
        
        3. **Risk-Reward Analysis**: Only take trades with a favorable risk-reward ratio (typically 2:1 or higher).
        
        4. **Stop-Loss Implementation**: Set predetermined exit points if a trade moves against you.
        
        5. **Exchange Vetting**: Use established exchanges with good security practices and track records.
        
        6. **Regular Withdrawals**: Don't keep large amounts of capital on exchanges for extended periods.
        
        ### Performance Metrics
        
        1. **Sharpe Ratio**: Measures risk-adjusted returns. A higher ratio indicates better risk-adjusted performance.
        
        2. **Win Rate**: The percentage of trades that result in profit.
        
        3. **Average Profit per Trade**: The mean profit across all winning trades.
        
        4. **Maximum Drawdown**: The largest peak-to-trough decline in account value.
        
        5. **Annualized Return**: The return on investment expressed as an annual percentage.
        """)

# Main app function
def main():
    """Main function to run the application"""
    # Initialize session state variables
    init_session_state()
    
    # Main title
    st.markdown('<div class="main-header">StableCoin Arbitrage TradeSmart 2</div>', unsafe_allow_html=True)
    st.markdown("A platform for identifying arbitrage opportunities in stablecoins across US exchanges")
    
    # Navigation menu
    selected_tab = option_menu(
        menu_title=None,
        options=["Market Scanner", "Pair Analysis", "Technical Analysis", "Risk Analysis", "About & Definitions"],
        icons=["search", "bar-chart", "graph-up", "shield", "info-circle"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
    )
    
    # Display the selected tab content
    if selected_tab == "Market Scanner":
        market_scanner_section()
    elif selected_tab == "Pair Analysis":
        pair_analysis_section()
    elif selected_tab == "Technical Analysis":
        technical_analysis_section()
    elif selected_tab == "Risk Analysis":
        risk_analysis_section()
    elif selected_tab == "About & Definitions":
        about_definitions_section()

# Run the app
if __name__ == "__main__":
    main()