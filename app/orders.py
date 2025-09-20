import math
import time
from dataclasses import dataclass
from binance.enums import SIDE_BUY, SIDE_SELL


def _round_step(qty, step):
    """Arrondit une quantité en fonction de la taille de pas."""
    if step == 0:
        return qty
    precision = max(int(round(-math.log10(step), 0)), 0)
    return float(f"{math.floor(qty / step) * step:.{precision}f}")


@dataclass
class RiskConfig:
    stop_loss_pct: float
    take_profit_pct: float
    max_orders_per_min: int


class OrderManager:
    def __init__(self, exchange, logger, risk: RiskConfig, dry_run=True):
        self.ex = exchange
        self.log = logger
        self.risk = risk
        self.dry_run = dry_run
        self._sent = []

    def _rate_limit_ok(self):
        now = time.time()
        self._sent = [t for t in self._sent if now - t < 60]
        return len(self._sent) < self.risk.max_orders_per_min

    def _mark_sent(self):
        self._sent.append(time.time())

    def calc_quantity_from_usdt(self, symbol, usdt_amount, price):
        info = self.ex.precision_info(symbol) or {'min_qty': 0.0, 'step_size': 0.0}
        raw_qty = usdt_amount / price
        qty = _round_step(raw_qty, info['step_size'])
        return max(qty, info['min_qty']) if info['min_qty'] else qty

    def market_buy(self, symbol, qty):
        if not self._rate_limit_ok():
            self.log.warning('Rate limit atteint, achat ignoré')
            return None
        self._mark_sent()
        if self.dry_run:
            self.log.info(f'[DRY-RUN] BUY {symbol} qty={qty}')
            return {'status': 'FILLED', 'orderId': 'DRYRUN-BUY'}
        try:
            order = self.ex.order_market(symbol, SIDE_BUY, qty)
            self.log.info(f'Ordre BUY envoyé: {order}')
            return order
        except Exception as e:
            self.log.exception(f'Echec BUY: {e}')
            return None

    def market_sell(self, symbol, qty):
        if not self._rate_limit_ok():
            self.log.warning('Rate limit atteint, vente ignorée')
            return None
        self._mark_sent()
        if self.dry_run:
            self.log.info(f'[DRY-RUN] SELL {symbol} qty={qty}')
            return {'status': 'FILLED', 'orderId': 'DRYRUN-SELL'}
        try:
            order = self.ex.order_market(symbol, SIDE_SELL, qty)
            self.log.info(f'Ordre SELL envoyé: {order}')
            return order
        except Exception as e:
            self.log.exception(f'Echec SELL: {e}')
            return None