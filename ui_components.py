"""
UI components for rendering charts and tables
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

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

def render_technical_chart(ta_data, exchange, stablecoin):
    """Render technical analysis chart"""
    if exchange in ta_data.columns:
        st.subheader("Price and Technical Indicators")
        
        # Create figure
        fig = go.Figure()
        
        # Add price
        fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data[exchange],
                                mode='lines', name=f"{stablecoin} Price"))
        
        # Add moving averages if available
        if 'SMA_5' in ta_data.columns:
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['SMA_5'],
                                    mode='lines', name='SMA (5)'))
        if 'SMA_20' in ta_data.columns:
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['SMA_20'],
                                    mode='lines', name='SMA (20)'))
        
        # Add Bollinger Bands if available
        if 'Upper_Band' in ta_data.columns and 'Lower_Band' in ta_data.columns:
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['Upper_Band'],
                                    mode='lines', name='Upper BB'))
            fig.add_trace(go.Scatter(x=ta_data.index, y=ta_data['Lower_Band'],
                                    mode='lines', name='Lower BB'))
        
        # Update layout
        fig.update_layout(
            title=f"{stablecoin} Technical Analysis on {exchange}",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            legend_title="Indicators",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)