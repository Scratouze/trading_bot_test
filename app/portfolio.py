from dataclasses import dataclass
from .exchange_binance import BinanceExchange

@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    entry_price: float = 0.0

    def is_open(self):
        return self.qty > 0

    def unrealized_pnl(self, last_price):
        if not self.is_open():
            return 0.0
        return (last_price - self.entry_price) * self.qty


def get_portfolio_value(ex: BinanceExchange, quote_asset='USDT'):
    total_value = 0.0
    prices = {}

    # Liste des actifs à surveiller
    assets = ['USDT', 'BTC', 'ETH', 'BNB']

    for asset in assets:
        balance = ex.get_asset_balance(asset)
        if asset == quote_asset:
            total_value += balance
        else:
            if asset not in prices:
                try:
                    prices[asset] = ex.get_symbol_price(f'{asset}{quote_asset}')
                except:
                    continue
            total_value += balance * prices[asset]

    return round(total_value, 4)
