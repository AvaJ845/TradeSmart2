# analysis_service.py
"""
Analysis services for finding arbitrage opportunities and analyzing price patterns
"""
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import zscore
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
        transaction_fees = {exchange: 0.001 for exchange in df['Exchange'].unique()}  # Default 0.1%
    
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
        z_scores[column] = deviations[column].rolling(window=window_size).apply(
            lambda x: (x.iloc[-1] - x.mean()) / x.std() if x.std() != 0 else 0
        )
    
    # Fill NaN values that appear in the beginning of the series
    z_scores = z_scores.fillna(0)
    
    return z_scores

def calculate_signals(z_scores, threshold=2.0):
    """
    Generate trading signals based on z-score thresholds
    
    Args:
        z_scores (pandas.DataFrame): DataFrame of z-scores
        threshold (float): Z-score threshold for signals
        
    Returns:
        tuple: (buy_signals, sell_signals) DataFrames
    """
    buy_signals = z_scores < -threshold
    sell_signals = z_scores > threshold
    
    return buy_signals, sell_signals

def estimate_convergence(z_scores, exchange):
    """
    Estimate probability of price convergence based on historical patterns
    
    Args:
        z_scores (pandas.DataFrame): DataFrame of z-scores
        exchange (str): Exchange name
        
    Returns:
        dict: Dictionary with convergence metrics
    """
    # Get z-score series for this exchange
    if exchange not in z_scores.columns:
        return {
            'Convergence Probability': 50.0,
            'Current Z-Score': 0.0,
            'Time to Converge (days)': 0.0
        }
    
    z_series = z_scores[exchange].dropna()
    
    if len(z_series) < 5:
        return {
            'Convergence Probability': 50.0,
            'Current Z-Score': z_series.iloc[-1] if len(z_series) > 0 else 0.0,
            'Time to Converge (days)': 0.0
        }
    
    # Count how many times extreme z-scores have reverted in the past
    extreme_count = sum((z_series.abs() > 1.5).astype(int))
    reversion_count = 0
    
    for i in range(len(z_series)-1):
        if abs(z_series.iloc[i]) > 1.5:
            if abs(z_series.iloc[i+1]) < abs(z_series.iloc[i]):
                reversion_count += 1
    
    # Calculate reversion probability
    if extreme_count > 0:
        reversion_prob = reversion_count / extreme_count
    else:
        reversion_prob = 0.5  # Default when no data
    
    # Current z-score
    current_z = z_series.iloc[-1]
    
    # Estimated time to convergence (in days)
    if abs(current_z) > 0.5:
        time_to_converge = min(5, abs(current_z)) * 0.5
    else:
        time_to_converge = 0
    
    return {
        'Convergence Probability': reversion_prob * 100,
        'Current Z-Score': current_z,
        'Time to Converge (days)': time_to_converge
    }

def backtest_arbitrage(historical_data, z_score_threshold=2.0, investment=1000):
    """
    Backtest a simple arbitrage strategy based on z-scores
    
    Args:
        historical_data (pandas.DataFrame): DataFrame with historical prices
        z_score_threshold (float): Z-score threshold for signals
        investment (float): Initial investment amount
        
    Returns:
        tuple: (portfolio_value, metrics) Series of portfolio values and performance metrics
    """
    # Calculate daily returns for each exchange
    returns = historical_data.pct_change().dropna()
    
    # Calculate daily z-scores
    z_scores = pd.DataFrame(index=returns.index)
    for col in returns.columns:
        z_scores[col] = (historical_data[col] - 1.0).rolling(10).apply(
            lambda x: stats.zscore(x)[-1] if len(x) > 1 and x.std() > 0 else 0
        )
    
    z_scores = z_scores.dropna()
    
    # Initialize portfolio and positions
    portfolio_value = [investment]
    positions = pd.DataFrame(0, index=z_scores.index, columns=z_scores.columns)
    
    # Simple strategy: buy when z-score < -threshold, sell when z-score > threshold
    for i in range(1, len(z_scores)):
        prev_date = z_scores.index[i-1]
        curr_date = z_scores.index[i]
        
        # Close positions if z-score crosses back
        for exchange in positions.columns:
            if positions.loc[prev_date, exchange] > 0 and z_scores.loc[curr_date, exchange] > 0:
                # Close long position
                positions.loc[curr_date, exchange] = 0
            elif positions.loc[prev_date, exchange] < 0 and z_scores.loc[curr_date, exchange] < 0:
                # Close short position
                positions.loc[curr_date, exchange] = 0
            else:
                # Maintain position
                positions.loc[curr_date, exchange] = positions.loc[prev_date, exchange]
        
        # Open new positions based on extreme z-scores
        for exchange in z_scores.columns:
            if z_scores.loc[curr_date, exchange] < -z_score_threshold and positions.loc[curr_date, exchange] == 0:
                # Buy signal
                positions.loc[curr_date, exchange] = 1
            elif z_scores.loc[curr_date, exchange] > z_score_threshold and positions.loc[curr_date, exchange] == 0:
                # Sell signal
                positions.loc[curr_date, exchange] = -1
        
        # Calculate portfolio value
        daily_return = sum(positions.loc[prev_date] * returns.loc[curr_date])
        portfolio_value.append(portfolio_value[-1] * (1 + daily_return))
    
    # Calculate performance metrics
    portfolio_returns = pd.Series(portfolio_value).pct_change().dropna()
    
    metrics = {
        'Final Value': portfolio_value[-1],
        'Total Return (%)': (portfolio_value[-1] / investment - 1) * 100,
        'Annualized Return (%)': portfolio_returns.mean() * 252 * 100,
        'Volatility (%)': portfolio_returns.std() * np.sqrt(252) * 100,
        'Sharpe Ratio': (portfolio_returns.mean() * 252) / (portfolio_returns.std() * np.sqrt(252)) if portfolio_returns.std() > 0 else 0,
        'Max Drawdown (%)': (pd.Series(portfolio_value).div(pd.Series(portfolio_value).cummax()) - 1).min() * 100
    }
    
    return pd.Series(portfolio_value, index=z_scores.index), metrics

def calculate_technical_indicators(df, exchange):
    """
    Calculate technical indicators for a price series
    
    Args:
        df (pandas.DataFrame): DataFrame with historical prices
        exchange (str): Exchange name to calculate indicators for
        
    Returns:
        pandas.DataFrame: DataFrame with technical indicators
    """
    # Create a copy to avoid modifying the original
    result = df.copy()
    
    # Basic indicators using pandas_ta instead of talib
    price_series = result[exchange]
    
    # Simple Moving Averages
    result['SMA_5'] = price_series.rolling(window=5).mean()
    result['SMA_20'] = price_series.rolling(window=20).mean()
    
    # RSI
    delta = price_series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    result['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = price_series.ewm(span=12, adjust=False).mean()
    ema26 = price_series.ewm(span=26, adjust=False).mean()
    result['MACD'] = ema12 - ema26
    result['MACD_Signal'] = result['MACD'].ewm(span=9, adjust=False).mean()
    result['MACD_Hist'] = result['MACD'] - result['MACD_Signal']
    
    # Bollinger Bands
    result['Middle_Band'] = result['SMA_20']
    result['Std_Dev'] = price_series.rolling(window=20).std()
    result['Upper_Band'] = result['Middle_Band'] + (result['Std_Dev'] * 2)
    result['Lower_Band'] = result['Middle_Band'] - (result['Std_Dev'] * 2)
    
    return result

def generate_signals_from_indicators(df):
    """
    Generate trading signals from technical indicators
    
    Args:
        df (pandas.DataFrame): DataFrame with technical indicators
        
    Returns:
        pandas.DataFrame: DataFrame with trading signals
    """
    signals = pd.DataFrame(index=df.index)
    
    # RSI signals
    signals['RSI_Signal'] = 0
    signals.loc[df['RSI'] < 30, 'RSI_Signal'] = 1  # Oversold - buy
    signals.loc[df['RSI'] > 70, 'RSI_Signal'] = -1  # Overbought - sell
    
    # MACD signals
    signals['MACD_Signal'] = 0
    signals.loc[df['MACD'] > df['MACD_Signal'], 'MACD_Signal'] = 1  # Bullish
    signals.loc[df['MACD'] < df['MACD_Signal'], 'MACD_Signal'] = -1  # Bearish
    
    # Bollinger Bands signals
    signals['BB_Signal'] = 0
    signals.loc[df[df.columns[0]] < df['Lower_Band'], 'BB_Signal'] = 1  # Price below lower band - buy
    signals.loc[df[df.columns[0]] > df['Upper_Band'], 'BB_Signal'] = -1  # Price above upper band - sell
    
    # Combined signal
    signals['Combined_Signal'] = signals.sum(axis=1)
    
    return signals
