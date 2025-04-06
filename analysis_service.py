"""
Analysis services for finding arbitrage opportunities and analyzing price patterns
"""
import pandas as pd
import numpy as np
from scipy import stats
from config import TRANSACTION_FEES, WITHDRAWAL_FEES

def find_arbitrage_opportunities(df, transaction_fees=None, withdrawal_fees=None):
    """
    Find arbitrage opportunities between exchanges
    
    Args:
        df (pandas.DataFrame): DataFrame with stablecoin prices
        transaction_fees (dict): Dictionary of transaction fees by exchange
        withdrawal_fees (dict): Dictionary of withdrawal fees by exchange and coin
        
    Returns:
        pandas.DataFrame: DataFrame of arbitrage opportunities
    """
    if transaction_fees is None:
        transaction_fees = TRANSACTION_FEES
    
    if withdrawal_fees is None:
        withdrawal_fees = WITHDRAWAL_FEES
    
    opportunities = []
    
    for coin in df['Stablecoin'].unique():
        coin_data = df[df['Stablecoin'] == coin]
        
        if len(coin_data) > 1:
            min_price_row = coin_data.loc[coin_data['Price'].idxmin()]
            max_price_row = coin_data.loc[coin_data['Price'].idxmax()]
            
            price_diff = max_price_row['Price'] - min_price_row['Price']
            percent_diff = (price_diff / min_price_row['Price']) * 100
            
            # Calculate fees
            buy_fee = min_price_row['Price'] * transaction_fees.get(min_price_row['Exchange'], 0.001)
            sell_fee = max_price_row['Price'] * transaction_fees.get(max_price_row['Exchange'], 0.001)
            
            # Add withdrawal fee if applicable
            withdrawal_fee = 0
            if withdrawal_fees:
                withdrawal_fee = withdrawal_fees.get(min_price_row['Exchange'], {}).get(coin, 0)
            
            # Calculate net price difference after fees
            net_price_diff = price_diff - buy_fee - sell_fee - (withdrawal_fee / 1000)  # Per $1000
            
            # Only consider meaningful differences (adjust threshold as needed)
            if net_price_diff > 0:
                opportunities.append({
                    'Stablecoin': coin,
                    'Buy Exchange': min_price_row['Exchange'],
                    'Buy Price': min_price_row['Price'],
                    'Sell Exchange': max_price_row['Exchange'],
                    'Sell Price': max_price_row['Price'],
                    'Price Difference': price_diff,
                    'Percent Difference': percent_diff,
                    'Transaction Fees': buy_fee + sell_fee,
                    'Withdrawal Fee': withdrawal_fee,
                    'Net Price Difference': net_price_diff,
                    'Potential Profit per $1000': (1000 / min_price_row['Price']) * net_price_diff
                })
    
    return pd.DataFrame(opportunities)

def calculate_z_scores(historical_data):
    """
    Calculate z-scores for price deviations from $1.00
    
    Args:
        historical_data (pandas.DataFrame): DataFrame with historical prices
        
    Returns:
        pandas.DataFrame: DataFrame of z-scores
    """
    # Calculate deviation from $1 for each exchange
    deviations = historical_data - 1.0
    
    # Calculate z-scores
    z_scores = pd.DataFrame(index=deviations.index)
    
    # Use rolling window to calculate z-scores to handle NaN values properly
    window_size = min(20, len(deviations))
    
    for column in deviations.columns:
        # Using rolling window to calculate z-scores
        rolling_mean = deviations[column].rolling(window=window_size).mean()
        rolling_std = deviations[column].rolling(window=window_size).std()
        z_scores[column] = (deviations[column] - rolling_mean) / rolling_std
        
        # Fill NaN values for the beginning of the series
        z_scores[column] = z_scores[column].fillna(0)
    
    return z_scores

def calculate_technical_indicators(df, exchange):
    """Basic technical indicators implementation"""
    # Create a copy to avoid modifying the original
    result = df.copy()
    
    # Price series
    price_series = result[exchange]
    
    # Simple Moving Averages
    result['SMA_5'] = price_series.rolling(window=5).mean()
    result['SMA_20'] = price_series.rolling(window=20).mean()
    
    # RSI calculation
    delta = price_series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    result['RSI'] = 100 - (100 / (1 + rs))
    result['RSI'] = result['RSI'].fillna(50)  # Fill NaN values
    
    # Bollinger Bands
    result['Middle_Band'] = result['SMA_20']
    result['Std_Dev'] = price_series.rolling(window=20).std()
    result['Upper_Band'] = result['Middle_Band'] + (result['Std_Dev'] * 2)
    result['Lower_Band'] = result['Middle_Band'] - (result['Std_Dev'] * 2)
    
    # MACD
    ema12 = price_series.ewm(span=12, adjust=False).mean()
    ema26 = price_series.ewm(span=26, adjust=False).mean()
    result['MACD'] = ema12 - ema26
    result['MACD_Signal'] = result['MACD'].ewm(span=9, adjust=False).mean()
    
    return result