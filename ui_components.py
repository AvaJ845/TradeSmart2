"""
UI components for rendering charts and tables
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots

def render_header():
    """Render the header of the application"""
    st.markdown('<div class="main-header">StableCoin Arbitrage TradeSmart 2</div>', unsafe_allow_html=True)
    st.markdown("A platform for identifying arbitrage opportunities in stablecoins across US exchanges")

def render_price_table(price_data, selected_stablecoins, selected_exchanges):
    """Render the price table"""
    filtered_data = price_data
    if selected_stablecoins:
        filtered_data = filtered_data[filtered_data['Stablecoin'].isin(selected_stablecoins)]
    if selected_exchanges:
        filtered_data = filtered_data[filtered_data['Exchange'].isin(selected_exchanges)]
    
    st.subheader("Current Stablecoin Prices")
    
    # Pivot table for prices
    price_pivot = filtered_data.pivot(index='Stablecoin', columns='Exchange', values='Price')
    st.dataframe(price_pivot.style.format("{:.6f}"), use_container_width=True)

def render_deviation_heatmap(price_data, selected_stablecoins, selected_exchanges):
    """Render the deviation heatmap"""
    filtered_data = price_data
    if selected_stablecoins:
        filtered_data = filtered_data[filtered_data['Stablecoin'].isin(selected_stablecoins)]
    if selected_exchanges:
        filtered_data = filtered_data[filtered_data['Exchange'].isin(selected_exchanges)]
    
    st.subheader("Price Deviation Heatmap (from $1.00)")
    
    # Pivot and create heatmap
    dev_pivot = filtered_data.pivot(index='Stablecoin', columns='Exchange', values='Deviation')
    
    fig = px.imshow(
        dev_pivot,
        color_continuous_scale='RdBu_r',
        labels=dict(x="Exchange", y="Stablecoin", color="Deviation"),
        zmin=-0.005, zmax=0.005
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def render_opportunities_table(opportunities_df):
    """Render the arbitrage opportunities table"""
    st.subheader("Arbitrage Opportunities")
    if not opportunities_df.empty:
        # Format and display opportunities
        display_df = opportunities_df.copy()
        
        # Format columns if they exist
        if 'Price Difference' in display_df.columns:
            display_df['Price Difference'] = display_df['Price Difference'].map('{:.6f}'.format)
        if 'Percent Difference' in display_df.columns:
            display_df['Percent Difference'] = display_df['Percent Difference'].map('{:.4f}%'.format)
        if 'Potential Profit per $1000' in display_df.columns:
            display_df['Potential Profit per $1000'] = display_df['Potential Profit per $1000'].map('${:.2f}'.format)
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No arbitrage opportunities found matching your criteria. Try adjusting your filters.")

def render_profit_chart(opportunities_df, profit_column='Potential Profit per $1000'):
    """Render the profit chart"""
    if not opportunities_df.empty and profit_column in opportunities_df.columns:
        fig = px.bar(
            opportunities_df,
            x='Stablecoin',
            y=profit_column,
            color=profit_column,
            hover_data=['Buy Exchange', 'Sell Exchange'],
            title=f'Potential Profit per $1000 Investment'
        )
        st.plotly_chart(fig, use_container_width=True)

def render_convergence_metrics(exchange_metrics, exchange_name):
    """Render convergence metrics for an exchange"""
    st.markdown('<div class="highlight">', unsafe_allow_html=True)
    st.subheader(f"{exchange_name} Metrics")
    st.metric("Current Z-Score", f"{exchange_metrics['Current Z-Score']:.2f}")
    st.metric("Convergence Probability", f"{exchange_metrics['Convergence Probability']:.1f}%")
    st.metric("Est. Time to Converge", f"{exchange_metrics['Time to Converge (days)']:.1f} days")
    st.markdown('</div>', unsafe_allow_html=True)

def render_trading_recommendation(z1, z2, exchange1, exchange2, stablecoin, convergence_metrics):
    """Render trading recommendation based on z-scores"""
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
            <p><strong>Expected Convergence:</strong> {max(convergence_metrics[0]['Convergence Probability'], convergence_metrics[1]['Convergence Probability']):.1f}% probability within {max(convergence_metrics[0]['Time to Converge (days)'], convergence_metrics[1]['Time to Converge (days)']):.1f} days</p>
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

def render_price_chart(hist_data, exchange1, exchange2, stablecoin):
    """Render price comparison chart"""
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

def render_price_spread_chart(hist_data, exchange1, exchange2):
    """Render price spread chart"""
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

def render_technical_chart(ta_data, exchange, stablecoin):
    """Render technical analysis chart"""
    st.subheader("Price and Technical Indicators")
    
    # Create figure with secondary y-axis for RSI
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.1,
                       row_heights=[0.7, 0.3])
    
    # Add price and moving averages
    fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data[exchange],
                            mode='lines', name=f"{stablecoin} Price"), row=1, col=1)
    
    if 'SMA_5' in ta_data.columns:
        fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['SMA_5'],
                                mode='lines', name='SMA (5)', line=dict(dash='dot')), row=1, col=1)
    
    if 'SMA_20' in ta_data.columns:
        fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['SMA_20'],
                                mode='lines', name='SMA (20)', line=dict(dash='dash')), row=1, col=1)
    
    # Add Bollinger Bands if available
    if 'Upper_Band' in ta_data.columns and 'Lower_Band' in ta_data.columns:
        fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['Upper_Band'],
                                mode='lines', name='Upper BB', line=dict(width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['Lower_Band'],
                                mode='lines', name='Lower BB', line=dict(width=1)), row=1, col=1)
    
    # Add RSI if available
    if 'RSI' in ta_data.columns:
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
    if 'RSI' in ta_data.columns:
        fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
    
    # Show plot
    st.plotly_chart(fig, use_container_width=True)

def render_signals_table(signal_df):
    """Render trading signals table"""
    st.subheader("Trading Signals")
    st.dataframe(signal_df, use_container_width=True)

def render_signal_summary(signals, stablecoin, exchange):
    """Render signal summary"""
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

def render_backtest_chart(portfolio_value):
    """Render backtest results chart"""
    fig = px.line(
        x=portfolio_value.index, 
        y=portfolio_value,
        labels={"x": "Date", "y": "Portfolio Value ($)"},
        title=f"Backtest Results: $1,000 Initial Investment"
    )
    st.plotly_chart(fig, use_container_width=True)

def render_risk_metrics(risk_metrics_df):
    """Render risk-adjusted metrics table"""
    st.subheader("Risk-Adjusted Metrics")
    st.dataframe(risk_metrics_df.style.background_gradient(subset=['Risk-Reward Ratio', 'Net Profit per $1000'], cmap='Blues'), use_container_width=True)

def render_position_sizing(position_df):
    """Render position sizing recommendations"""
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
