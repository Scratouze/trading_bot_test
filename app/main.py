import os
import time
import yaml
from dotenv import load_dotenv

from .logger import setup_logger
from .exchange_binance import BinanceExchange
from .orders import OrderManager, RiskConfig
from .portfolio import Position
from .market import poll_klines
from .strategy.sma_crossover import SmaCrossover, SmaParams
from trading_bot.app.trade_logger import log_trade

import sys
if hasattr(sys.stdout, "reconfigure"):
    # On laisse l'encodage par defaut de la console Windows (CP-1252).
    # Tous les logs ci-dessous sont en ASCII pur.
    pass


def env_bool(name, default='true'):
    return os.getenv(name, default).lower() == 'true'


class Bot:
    def __init__(self):
        load_dotenv()

        # Config YAML (niveau de log, fichier, etc.)
        with open('trading_bot/config.yaml', 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        self.log = setup_logger(cfg['logging']['level'], cfg['logging']['file'])
        self.total_pnl = 0.0

        # Parametres principaux
        self.symbol = os.getenv('SYMBOL', 'BTCUSDT')
        self.interval = os.getenv('INTERVAL', '1m')
        self.poll_seconds = int(os.getenv('POLL_SECONDS', '4'))
        self.base_order_usdt = float(os.getenv('BASE_ORDER_USDT', '25'))
        dry_run = env_bool('DRY_RUN', 'true')
        testnet = env_bool('BINANCE_TESTNET', 'true')

        # Exchange
        bx_cfg = BinanceExchange.env_from_os(testnet)
        self.ex = BinanceExchange(bx_cfg)

        # Strategie SMA
        sma_short = int(os.getenv('SMA_SHORT', '20'))
        sma_long = int(os.getenv('SMA_LONG', '50'))
        sma_seuil_min_usdt = float(os.getenv('SMA_SEUIL_MIN', '50'))   # en USDT
        sma_seuil_pct = float(os.getenv('SMA_SEUIL_PCT', '0.0005'))    # 0.05%
        sma_confirm = int(os.getenv('SMA_CONFIRM_BARS', '3'))

        self.strategy = SmaCrossover(
            SmaParams(
                short=sma_short,
                long=sma_long,
                min_gap_usdt=sma_seuil_min_usdt,
                min_gap_pct=sma_seuil_pct,
                confirm_bars=sma_confirm
            ),
            log=self.log
        )

        # Logs init (ASCII only)
        self.log.info("")
        self.log.info("[STRATEGIE] SMA%d / SMA%d | seuils: %.2f USDT ou %.3f%% | confirmations: %d",
                      sma_short, sma_long, sma_seuil_min_usdt, sma_seuil_pct * 100, sma_confirm)
        self.log.info("[INIT] Bot initialise : symbol=%s | interval=%s | dry_run=%s | testnet=%s",
                      self.symbol, self.interval, str(dry_run), str(testnet))
        self.log.info("")

        # Risque
        self.risk = RiskConfig(
            stop_loss_pct=float(os.getenv('STOP_LOSS_PCT', '0.03')),
            take_profit_pct=float(os.getenv('TAKE_PROFIT_PCT', '0.06')),
            max_orders_per_min=int(os.getenv('MAX_OPEN_ORDERS_PER_MIN', '3')),
        )
        self.om = OrderManager(self.ex, self.log, self.risk, dry_run=dry_run)
        self.pos = Position(symbol=self.symbol)

    def run_forever(self):
        self.log.info("[LOOP] Boucle de trading demarree.")
        while True:
            try:
                self.log.info("")
                self.log.info("[TICK] Nouveau tick...")

                # 1) Market data
                df = poll_klines(self.ex, self.symbol, self.interval, limit=200)
                df = self.strategy.compute(df)

                # 2) Strategie
                sig = self.strategy.signal(df)

                last = df.iloc[-1]
                prev = df.iloc[-2]
                price = float(last["close"])
                sma_s = float(last["sma_short"])
                sma_l = float(last["sma_long"])
                gap = sma_s - sma_l
                prev_gap = float(prev["sma_short"]) - float(prev["sma_long"])
                threshold = max(
                    self.strategy.p.min_gap_usdt,
                    price * self.strategy.p.min_gap_pct
                )

                # 3) Logs lisibles
                self.log.info("[SMA] %s %s", self.symbol, self.interval)
                self.log.info("   Dernier prix : %.2f USDT", price)
                self.log.info("   SMA%d = %.2f | SMA%d = %.2f", self.strategy.p.short, sma_s, self.strategy.p.long, sma_l)
                self.log.info("   Ecart SMA : %+.2f | Seuil requis >= %.2f", gap, threshold)

                info = getattr(self.strategy, "last_info", {}) or {}
                trend = info.get("trend", "?")
                cross = info.get("cross", "none")
                why = info.get("why", "")
                confirm_need = int(info.get("confirm_needed", self.strategy.p.confirm_bars))
                confirm_cnt = int(info.get("confirm_count", 0))
                near = bool(info.get("near_cross", False))

                if sig in ("BUY", "SELL"):
                    self.log.info("[ACTION] Signal %s valide.", sig)
                else:
                    self.log.info("[INFO] Aucun signal.")
                    self.log.info("   Tendance : %s | Croisement : %s | Confirmation : %d/%d",
                                  trend, cross, confirm_cnt, confirm_need)
                    if near:
                        self.log.info("   Alerte: croisement proche (retournement detecte, seuil non atteint).")
                    if why:
                        self.log.info("   Raison : %s", why)

                # 4) Execution
                last_price = price
                if sig == 'BUY' and not self.pos.is_open():
                    qty = self.om.calc_quantity_from_usdt(self.symbol, self.base_order_usdt, last_price)
                    if qty > 0 and self.om.market_buy(self.symbol, qty):
                        self.pos.qty = qty
                        self.pos.entry_price = last_price
                        self.log.info("[POSITION] Ouverte: qty=%s @ %.2f", qty, last_price)
                        log_trade(symbol=self.symbol, side="BUY", price=last_price, quantity=qty)

                elif sig == 'SELL':
                    if self.pos.is_open():
                        if self.om.market_sell(self.symbol, self.pos.qty):
                            pnl = self.pos.unrealized_pnl(last_price)
                            self.total_pnl += pnl
                            self.log.info("[POSITION] Fermee | PnL ~= %.2f USDT | PnL total : %.2f USDT",
                                          pnl, self.total_pnl)
                            self.pos = Position(symbol=self.symbol)
                    else:
                        self.log.info("[VENTE] Signal SELL ignore (aucune position ouverte).")

                # 5) SL / TP
                if self.pos.is_open():
                    pnl_pct = (last_price - self.pos.entry_price) / self.pos.entry_price
                    if pnl_pct <= -self.risk.stop_loss_pct:
                        self.log.warning("[RISK] Stop-loss declenche.")
                        self.om.market_sell(self.symbol, self.pos.qty)
                        self.pos = Position(symbol=self.symbol)
                    elif pnl_pct >= self.risk.take_profit_pct:
                        self.log.info("[RISK] Take-profit atteint.")
                        self.om.market_sell(self.symbol, self.pos.qty)
                        self.pos = Position(symbol=self.symbol)

            except KeyboardInterrupt:
                self.log.info("[EXIT] Arret manuel (CTRL+C).")
                break
            except Exception as e:
                self.log.exception("[ERROR] Boucle: erreur inattendue: %s", e)

            time.sleep(self.poll_seconds)


if __name__ == '__main__':
    Bot().run_forever()
