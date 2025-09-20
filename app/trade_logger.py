# trading_bot/app/trade_logger.py
import csv
import os
from datetime import datetime

TRADE_LOG_FILE = "trades.csv"


def log_trade(symbol: str, side: str, price: float, quantity: float, pnl: float = None):
    is_new = not os.path.exists(TRADE_LOG_FILE)
    with open(TRADE_LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        if is_new:
            writer.writerow(["timestamp", "symbol", "side", "price", "quantity", "pnl"])
        writer.writerow([
            datetime.utcnow().isoformat(),
            symbol,
            side,
            price,
            quantity,
            round(pnl, 4) if pnl is not None else ""
        ])


def read_trades():
    if not os.path.exists(TRADE_LOG_FILE):
        return []
    with open(TRADE_LOG_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        return list(reader)


def compute_stats():
    trades = read_trades()
    wins, losses = 0, 0
    profit, loss = 0.0, 0.0
    total_pnl = 0.0

    for trade in trades:
        pnl = trade.get("pnl")
        if pnl is None or pnl == "":
            continue
        pnl = float(pnl)
        total_pnl += pnl
        if pnl >= 0:
            wins += 1
            profit += pnl
        else:
            losses += 1
            loss += pnl

    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0

    return {
        "total_pnl": round(total_pnl, 4),
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "profit": round(profit, 4),
        "loss": round(loss, 4),
    }
