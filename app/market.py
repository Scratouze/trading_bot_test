import pandas as pd

def klines_to_df(klines):
    """Convertit les bougies Binance en DataFrame pandas."""
    cols = [
        'open_time',
        'open',
        'high',
        'low',
        'close',
        'volume',
        'close_time',
        'quote_asset_volume',
        'number_of_trades',
        'taker_buy_base',
        'taker_buy_quote',
        'ignore',
    ]
    df = pd.DataFrame(klines, columns=cols)
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    return df

def poll_klines(exchange, symbol, interval, limit=200):
    """Récupère les dernières bougies et retourne un DataFrame."""
    klines = exchange.fetch_klines(symbol, interval, limit)
    return klines_to_df(klines)