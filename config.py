"""
Configuration settings for the StableCoin Arbitrage TradeSmart 2 platform
"""

# Supported exchanges
SUPPORTED_EXCHANGES = ['coinbase', 'uphold', 'kraken', 'binance.us', 'gemini']

# Supported stablecoins
STABLECOINS = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'GUSD', 'FRAX', 'LUSD', 'sUSD', 'RLUSD']

# Transaction fees by exchange (% as decimal)
TRANSACTION_FEES = {
    'coinbase': 0.006,  # 0.6% for small trades
    'uphold': 0.0025,   # 0.25%
    'kraken': 0.0026,   # 0.26% for small trades
    'binance.us': 0.001, # 0.1%
    'gemini': 0.0035    # 0.35% for small trades
}

# Withdrawal fees by exchange and coin (in USD)
WITHDRAWAL_FEES = {
    'coinbase': {
        'USDT': 5.0,
        'USDC': 0.0,  # Free USDC withdrawals
        'BUSD': 2.5,
        'DAI': 3.0,
        'TUSD': 2.5,
        'USDP': 3.0,
        'GUSD': 2.5,
        'FRAX': 3.0,
        'LUSD': 3.0,
        'sUSD': 3.0,
        'RLUSD': 3.0  # Added RLUSD
    },
    'uphold': {
        'USDT': 4.0,
        'USDC': 4.0,
        'BUSD': 4.0,
        'DAI': 4.0,
        'TUSD': 4.0,
        'RLUSD': 4.0  # Added RLUSD
    },
    'kraken': {
        'USDT': 5.0,
        'USDC': 2.5,
        'DAI': 3.0,
        'BUSD': 3.0,
        'RLUSD': 3.0  # Added RLUSD
    },
    'binance.us': {
        'USDT': 8.0,
        'USDC': 8.0,
        'BUSD': 0.0,  # Binance typically has free BUSD withdrawals
        'DAI': 10.0,
        'RLUSD': 8.0  # Added RLUSD
    },
    'gemini': {
        'USDT': 0.0,  # Gemini offers some free withdrawals per month
        'USDC': 0.0,
        'DAI': 0.0,
        'GUSD': 0.0,
        'RLUSD': 0.0  # Added RLUSD
    }
}
