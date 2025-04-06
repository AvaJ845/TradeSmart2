# risk_service.py
"""
Risk management services for analyzing and optimizing trading strategies
"""
import pandas as pd
import numpy as np
from config import TRANSACTION_FEES, WITHDRAWAL_FEES

def calculate_trade_metrics(opportunities_df):
    """
    Calculate risk-adjusted metrics for trading opportunities
    
    Args:
        opportunities_df (pandas.DataFrame): DataFrame of arbitrage opportunities
        
    Returns:
        pandas.DataFrame: DataFrame with risk metrics
    """
    if opportunities_df.empty:
        return pd.DataFrame()
    
    metrics = []
    
    for _, row in opportunities_df.iterrows():
        # Estimate transaction costs
        transaction_cost = row.get('Transaction Fees', 0)
        withdrawal_fee = row.get('Withdrawal Fee', 0)
        
        # Net profit after transaction costs
        net_profit = row['Price Difference'] - transaction_cost - (withdrawal_fee / 1000)
        profit_per_1000 = (1000 / row['Buy Price']) * net_profit
        
        # Risk estimation (simplified)
        max_adverse_move = 0.001  # Assume 0.1% adverse price movement
        risk_amount = (1000 / row['Buy Price']) * max_adverse_move
        
        # Add counterparty risk factor based on exchange
        exchange_risk_factors = {
            'coinbase': 0.8,    # Lower risk (established exchange)
            'kraken': 0.9,
            'binance.us': 0.85,
            'gemini': 0.9,
            'uphold': 1.2       # Higher risk (smaller exchange)
        }
        
        buy_exchange_risk = exchange_risk_factors.get(row['Buy Exchange'], 1.0)
        sell_exchange_risk = exchange_risk_factors.get(row['Sell Exchange'], 1.0)
        
        # Combine exchange risks (weighted average)
        combined_risk_factor = (buy_exchange_risk + sell_exchange_risk) / 2
        
        # Adjust risk amount by exchange risk factor
        adjusted_risk = risk_amount * combined_risk_factor
        
        # Risk-reward ratio
        if adjusted_risk > 0:
            risk_reward = profit_per_1000 / adjusted_risk
        else:
            risk_reward = float('inf')
        
        # Annualized return (assuming 1 day holding period)
        annualized_return = profit_per_1000 / 1000 * 365 * 100
        
        metrics.append({
            'Stablecoin': row['Stablecoin'],
            'Buy Exchange': row['Buy Exchange'],
            'Sell Exchange': row['Sell Exchange'],
            'Gross Profit per $1000': row['Potential Profit per $1000'],
            'Est. Transaction Cost': transaction_cost * (1000 / row['Buy Price']),
            'Withdrawal Fee (per trade)': withdrawal_fee,
            'Net Profit per $1000': profit_per_1000,
            'Risk Amount per $1000': adjusted_risk,
            'Combined Exchange Risk Factor': combined_risk_factor,
            'Risk-Reward Ratio': risk_reward,
            'Annualized Return (%)': annualized_return,
            'Break-Even Time (hours)': 24 / (profit_per_1000 / adjusted_risk) if adjusted_risk > 0 else 0
        })
    
    return pd.DataFrame(metrics)

def calculate_optimal_position_size(trade_metrics, total_capital, max_risk_pct, 
                                  max_portfolio_pct, use_stop_loss=True, stop_loss_pct=0.5):
    """
    Calculate optimal position size based on risk parameters
    
    Args:
        trade_metrics (pandas.DataFrame): DataFrame with trade metrics
        total_capital (float): Total available capital
        max_risk_pct (float): Maximum risk per trade as percentage
        max_portfolio_pct (float): Maximum portfolio allocation per trade as percentage
        use_stop_loss (bool): Whether to use stop loss
        stop_loss_pct (float): Stop loss percentage
        
    Returns:
        pandas.DataFrame: DataFrame with position sizing recommendations
    """
    if trade_metrics.empty:
        return pd.DataFrame()
    
    results = []
    
    for _, row in trade_metrics.iterrows():
        # Maximum position based on risk
        max_risk_amount = total_capital * (max_risk_pct / 100)
        
        # Calculate effective risk
        risk_per_dollar = row["Risk Amount per $1000"] / 1000
        if use_stop_loss:
            # Use the minimum of actual risk and stop loss
            effective_risk = min(risk_per_dollar, stop_loss_pct / 100)
        else:
            effective_risk = risk_per_dollar
        
        # Account for exchange risk factor
        adjusted_risk = effective_risk * row["Combined Exchange Risk Factor"]
        
        position_size_risk = max_risk_amount / (adjusted_risk * 1000) * 1000
        
        # Maximum position based on portfolio allocation
        max_allocation = total_capital * (max_portfolio_pct / 100)
        
        # Choose the smaller of the two
        recommended_position = min(position_size_risk, max_allocation)
        
        # Add execution risk factor
        execution_risk_factor = 0.9  # Assume 10% reduction in profit due to execution risk
        
        # Calculate expected profit
        expected_profit = (recommended_position / 1000 * row["Net Profit per $1000"]) * execution_risk_factor
        
        # Add withdrawal and transaction costs
        transaction_costs = row["Est. Transaction Cost"] * (recommended_position / 1000)
        withdrawal_cost = row["Withdrawal Fee (per trade)"]
        
        # Adjusted net profit
        adjusted_profit = expected_profit - withdrawal_cost
        
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
    
    return pd.DataFrame(results)
