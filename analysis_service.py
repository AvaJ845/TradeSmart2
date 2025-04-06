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
                    'Potential Profit per $1000': (1000 / min_price_row['Price']) * net_price_diff,
                    'Adjusted Profit per $1000': (1000 / min_price_row['Price']) * net_price_diff  # Adding this to match app.py expectations
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

def calculate_signals(z_scores, threshold=2.0):
    """
    Calculate trading signals based on z-scores
    
    Args:
        z_scores (pandas.DataFrame): DataFrame of z-scores
        threshold (float): Z-score threshold for signals
        
    Returns:
        pandas.DataFrame: DataFrame of trading signals
    """
    signals = pd.DataFrame(index=z_scores.index)
    
    for column in z_scores.columns:
        # Generate signals: 1 for buy (z-score < -threshold), -1 for sell (z-score > threshold), 0 for hold
        signals[column] = np.where(z_scores[column] < -threshold, 1, 
                               np.where(z_scores[column] > threshold, -1, 0))
    
    return signals

def estimate_convergence(z_scores, exchange):
    """
    Estimate probability and time for price convergence
    
    Args:
        z_scores (pandas.DataFrame): DataFrame of z-scores
        exchange (str): Exchange name
        
    Returns:
        dict: Convergence metrics
    """
    if exchange not in z_scores.columns:
        return {
            'Current Z-Score': 0,
            'Convergence Probability': 0,
            'Time to Converge (days)': float('inf')
        }
    
    current_z = z_scores[exchange].iloc[-1]
    
    # Calculate probability of convergence based on z-score
    # Using cumulative normal distribution for probability
    convergence_prob = stats.norm.cdf(-abs(current_z)) * 2 * 100  # In percentage
    
    # Estimate time to convergence based on historical mean reversion
    # Simple model: larger z-scores take longer to converge
    if abs(current_z) < 0.5:
        time_to_converge = 1  # Quick convergence for small deviations
    else:
        time_to_converge = min(30, abs(current_z) * 3)  # Estimate days to converge
    
    return {
        'Current Z-Score': current_z,
        'Convergence Probability': convergence_prob,
        'Time to Converge (days)': time_to_converge
    }

def calculate_technical_indicators(df, exchange):
    """
    Calculate technical indicators for a given price series
    
    Args:
        df (pandas.DataFrame): DataFrame with price data
        exchange (str): Exchange name
        
    Returns:
        pandas.DataFrame: DataFrame with technical indicators
    """
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

def generate_signals_from_indicators(ta_data):
    """
    Generate trading signals from technical indicators
    
    Args:
        ta_data (pandas.DataFrame): DataFrame with technical indicators
        
    Returns:
        pandas.DataFrame: DataFrame with trading signals
    """
    signals = pd.DataFrame(index=ta_data.index)
    
    # RSI signals
    signals['RSI_Signal'] = np.where(ta_data['RSI'] < 30, 1,  # Oversold (buy)
                                  np.where(ta_data['RSI'] > 70, -1, 0))  # Overbought (sell)
    
    # MACD signals
    signals['MACD_Signal'] = np.where(ta_data['MACD'] > ta_data['MACD_Signal'], 1, 
                                    np.where(ta_data['MACD'] < ta_data['MACD_Signal'], -1, 0))
    
    # Bollinger Bands signals
    price_col = [col for col in ta_data.columns if col not in ['SMA_5', 'SMA_20', 'RSI', 
                                                              'Middle_Band', 'Std_Dev', 
                                                              'Upper_Band', 'Lower_Band',
                                                              'MACD', 'MACD_Signal']][0]
    
    signals['BB_Signal'] = np.where(ta_data[price_col] < ta_data['Lower_Band'], 1,  # Price below lower band (buy)
                                  np.where(ta_data[price_col] > ta_data['Upper_Band'], -1, 0))  # Price above upper band (sell)
    
    # Combined signal
    signals['Combined_Signal'] = signals['RSI_Signal'] + signals['MACD_Signal'] + signals['BB_Signal']
    
    return signals

def backtest_arbitrage(price_data, z_score_threshold=2.0, investment=1000):
    """
    Backtest a simple mean-reversion arbitrage strategy
    
    Args:
        price_data (pandas.DataFrame): DataFrame with historical prices
        z_score_threshold (float): Z-score threshold for trading signals
        investment (float): Initial investment amount
        
    Returns:
        tuple: (portfolio_value, performance_metrics)
    """
    # Calculate z-scores
    deviations = price_data - 1.0
    rolling_mean = deviations.rolling(window=20).mean()
    rolling_std = deviations.rolling(window=20).std()
    z_scores = (deviations - rolling_mean) / rolling_std
    z_scores = z_scores.fillna(0)
    
    # Generate signals
    signals = pd.DataFrame(0, index=z_scores.index, columns=z_scores.columns)
    
    for column in z_scores.columns:
        signals[column] = np.where(z_scores[column] < -z_score_threshold, 1,  # Buy signal
                                np.where(z_scores[column] > z_score_threshold, -1, 0))  # Sell signal
    
    # Initialize portfolio
    portfolio_value = pd.Series(investment, index=price_data.index)
    positions = pd.DataFrame(0, index=price_data.index, columns=price_data.columns)
    cash = pd.Series(investment, index=price_data.index)
    
    # Simulate trading
    for i in range(1, len(price_data)):
        # Update positions based on signals
        for column in price_data.columns:
            prev_position = positions.iloc[i-1, positions.columns.get_loc(column)]
            
            # Get signal
            signal = signals.iloc[i, signals.columns.get_loc(column)]
            
            # Execute trades
            if signal == 1 and prev_position <= 0:  # Buy signal
                # Close short position if exists
                if prev_position < 0:
                    cash.iloc[i] = cash.iloc[i-1] + prev_position * price_data.iloc[i, price_data.columns.get_loc(column)]
                    positions.iloc[i, positions.columns.get_loc(column)] = 0
                
                # Buy with 90% of available cash
                buy_amount = cash.iloc[i] * 0.9
                positions.iloc[i, positions.columns.get_loc(column)] = buy_amount / price_data.iloc[i, price_data.columns.get_loc(column)]
                cash.iloc[i] = cash.iloc[i] - buy_amount
                
            elif signal == -1 and prev_position >= 0:  # Sell signal
                # Close long position if exists
                if prev_position > 0:
                    cash.iloc[i] = cash.iloc[i-1] + prev_position * price_data.iloc[i, price_data.columns.get_loc(column)]
                    positions.iloc[i, positions.columns.get_loc(column)] = 0
                
                # Short with 90% of available cash
                sell_amount = cash.iloc[i] * 0.9
                positions.iloc[i, positions.columns.get_loc(column)] = -sell_amount / price_data.iloc[i, price_data.columns.get_loc(column)]
                cash.iloc[i] = cash.iloc[i] - sell_amount
                
            else:  # Hold
                positions.iloc[i, positions.columns.get_loc(column)] = prev_position
                cash.iloc[i] = cash.iloc[i-1]
        
        # Calculate portfolio value
        position_value = 0
        for column in price_data.columns:
            position_value += positions.iloc[i, positions.columns.get_loc(column)] * price_data.iloc[i, price_data.columns.get_loc(column)]
        
        portfolio_value.iloc[i] = cash.iloc[i] + position_value
    
    # Calculate performance metrics
    start_value = portfolio_value.iloc[0]
    end_value = portfolio_value.iloc[-1]
    total_return = (end_value / start_value - 1) * 100
    
    # Annualized return
    days = (price_data.index[-1] - price_data.index[0]).days
    if days > 0:
        years = days / 365
        annualized_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100
    else:
        annualized_return = 0
    
    # Daily returns
    daily_returns = portfolio_value.pct_change().dropna()
    
    # Sharpe ratio (assuming risk-free rate of 0%)
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)  # Annualized
    else:
        sharpe_ratio = 0
    
    metrics = {
        'Final Value': end_value,
        'Total Return (%)': total_return,
        'Annualized Return (%)': annualized_return,
        'Sharpe Ratio': sharpe_ratio
    }
    
    return portfolio_value, metrics
