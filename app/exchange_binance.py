import os
from dataclasses import dataclass
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET


@dataclass
class BinanceConfig:
    api_key: str
    api_secret: str
    testnet: bool = True


class BinanceExchange:
    """Wrapper léger autour de l'API Binance."""

    def __init__(self, cfg: BinanceConfig):
        self.cfg = cfg
        self.client = Client(cfg.api_key, cfg.api_secret, testnet=cfg.testnet)
        if cfg.testnet:
            # Force URL vers l’API testnet (spot)
            self.client.API_URL = 'https://testnet.binance.vision/api'

    def get_symbol_price(self, symbol: str) -> float:
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])

    def fetch_klines(self, symbol: str, interval: str = '1m', limit: int = 200):
        return self.client.get_klines(symbol=symbol, interval=interval, limit=limit)

    def get_asset_balance(self, asset: str) -> float:
        bal = self.client.get_asset_balance(asset=asset)
        if not bal:
            return 0.0
        return float(bal.get('free', 0))

    def order_market(self, symbol: str, side: str, quantity: float):
        return self.client.create_order(symbol=symbol, side=side, type=ORDER_TYPE_MARKET, quantity=quantity)

    def precision_info(self, symbol: str):
        info = self.client.get_symbol_info(symbol)
        if not info:
            return None
        lot_filter = next((f for f in info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
        min_qty = float(lot_filter['minQty']) if lot_filter else 0.0
        step_size = float(lot_filter['stepSize']) if lot_filter else 0.0
        return {'min_qty': min_qty, 'step_size': step_size}

    @staticmethod
    def env_from_os(testnet: bool):
        if testnet:
            return BinanceConfig(
                api_key=os.getenv('BINANCE_TESTNET_API_KEY', ''),
                api_secret=os.getenv('BINANCE_TESTNET_API_SECRET', ''),
                testnet=True,
            )
        return BinanceConfig(
            api_key=os.getenv('BINANCE_API_KEY', ''),
            api_secret=os.getenv('BINANCE_API_SECRET', ''),
            testnet=False,
        )