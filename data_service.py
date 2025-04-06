"""
Data service for fetching and processing stablecoin data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from config import SUPPORTED_EXCHANGES, STABLECOINS

def fetch_stablecoin_prices(simulation_mode=True, api_keys=None):
    """
    Fetch current stablecoin prices from supported exchanges
    
    Args:
        simulation_mode (bool): Whether to use synthetic data for demonstration
        api_keys (dict): Dictionary of API keys for each exchange
        
    Returns:
        pandas.DataFrame: DataFrame of stablecoin prices across exchanges
    """
    if simulation_mode:
        return _generate_synthetic_price_data()
    
    # In a real implementation, this would make API calls
    # For now, just return synthetic data
    return _generate_synthetic_price_data()

def _generate_synthetic_price_data():
    """Generate synthetic price data for demonstration purposes"""
    data = []
    timestamp = datetime.now()
    
    for exchange in SUPPORTED_EXCHANGES:
        # Generate a small exchange-specific bias
        exchange_bias = np.random.normal(0, 0.0002)
        
        for coin in STABLECOINS:
            # Generate random price with slight deviation from $1
            if random.random() < 0.9:  # 90% chance of having data for this pair
                # Most prices stay very close to $1
                if random.random() < 0.8:
                    price = 1.0 + np.random.normal(exchange_bias, 0.0005)
                else:
                    # Some prices have larger deviations to create arbitrage opportunities
                    price = 1.0 + np.random.normal(exchange_bias, 0.002)
                    
                # Ensure price is positive and reasonable
                price = max(0.95, min(1.05, price))
                
                data.append({
                    'Exchange': exchange,
                    'Stablecoin': coin,
                    'Price': price,
                    'Deviation': price - 1.0,
                    'Timestamp': timestamp
                })
    
    return pd.DataFrame(data)

def fetch_historical_data(stablecoin, days=30, simulation_mode=True):
    """
    Fetch or simulate historical price data for stablecoins
    
    Args:
        stablecoin (str): The stablecoin symbol
        days (int): Number of days of historical data
        simulation_mode (bool): Whether to use synthetic data
        
    Returns:
        pandas.DataFrame: DataFrame with historical prices
    """
    # Generate synthetic data with small fluctuations around $1
    np.random.seed(hash(stablecoin) % 10000)  # Different seed for each stablecoin
    date_range = pd.date_range(end=datetime.now(), periods=days)
    
    data = {}
    for exchange in SUPPORTED_EXCHANGES:
        # Create exchange-specific bias
        exchange_bias = np.random.normal(0, 0.0002)
        
        # Create base price with small random walk
        price = 1.0
        prices = []
        
        for _ in range(days):
            # Small random walk
            price += np.random.normal(0, 0.0002)
            
            # Add mean reversion to $1
            price = price * 0.9 + 1.0 * 0.1
            
            # Add exchange-specific bias
            adjusted_price = price + exchange_bias
            
            # Add some noise
            adjusted_price += np.random.normal(0, 0.0001)
            
            prices.append(adjusted_price)
        
        # Add some spikes to simulate occasional arbitrage opportunities
        spike_idx = np.random.randint(0, days, 3)
        spike_direction = np.random.choice([-1, 1], 3)
        for i, direction in zip(spike_idx, spike_direction):
            prices[i] += direction * np.random.uniform(0.001, 0.003)
        
        data[exchange] = pd.Series(prices, index=date_range)
    
    return pd.DataFrame(data)

def estimate_slippage(stablecoin, buy_exchange, sell_exchange, trade_size, simulation_mode=True):
    """
    Estimate slippage for a given trade size
    
    Args:
        stablecoin (str): The stablecoin symbol
        buy_exchange (str): Exchange where the coin is bought
        sell_exchange (str): Exchange where the coin is sold
        trade_size (float): Size of the trade in USD
        simulation_mode (bool): Whether to use synthetic data
        
    Returns:
        float: Estimated slippage in USD
    """
    # Simulate slippage based on trade size
    # Larger trades have higher slippage
    buy_slippage = trade_size * 0.0001 * (1 + random.random())  # 0.01% - 0.02% slippage
    sell_slippage = trade_size * 0.0001 * (1 + random.random())  # 0.01% - 0.02% slippage
    
    # Add exchange-specific factors
    exchange_factors = {
        'coinbase': 0.8,    # Lower slippage due to high liquidity
        'kraken': 0.9,
        'binance.us': 0.7,  # Lowest slippage
        'gemini': 1.1,
        'uphold': 1.3       # Higher slippage
    }
    
    buy_slippage *= exchange_factors.get(buy_exchange, 1.0)
    sell_slippage *= exchange_factors.get(sell_exchange, 1.0)
    
    # Add stablecoin-specific factors
    coin_factors = {
        'USDT': 0.8,  # High liquidity
        'USDC': 0.9,  # High liquidity
        'BUSD': 1.1,
        'DAI': 1.2,
        'TUSD': 1.3,
        'USDP': 1.4,
        'GUSD': 1.5,
        'FRAX': 1.3,
        'LUSD': 1.6,
        'sUSD': 1.7   # Lower liquidity, higher slippage
    }
    
    combined_slippage = (buy_slippage + sell_slippage) * coin_factors.get(stablecoin, 1.0)
    
    return combined_slippage