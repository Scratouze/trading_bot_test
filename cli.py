import typer
from trading_bot.app.main import Bot
from trading_bot.app.exchange_binance import BinanceExchange
from trading_bot.app.portfolio import get_portfolio_value
import os
from dotenv import load_dotenv

load_dotenv()

# print("API KEY:", os.getenv("BINANCE_TESTNET_API_KEY"))
# print("SECRET:", os.getenv("BINANCE_TESTNET_API_SECRET"))

app = typer.Typer()

@app.command()
def start():
    portfolio()
    Bot().run_forever()

@app.command()
def balance():
    cfg = BinanceExchange.env_from_os(testnet=True)  # change en False si tu veux réel
    ex = BinanceExchange(cfg)

    print("\n--- Solde du compte testnet ---")
    for asset in ['USDT', 'BTC', 'ETH', 'BNB']:  # ajoute d'autres si tu veux
        bal = ex.get_asset_balance(asset)
        if bal > 0:
            print(f"{asset}: {bal}")

@app.command()
def portfolio():
    cfg = BinanceExchange.env_from_os(testnet=True)
    ex = BinanceExchange(cfg)

    value = get_portfolio_value(ex)
    print(f"\n💰 Valeur totale du portefeuille (en USDT): {value}")

@app.command()
def stats():
    from trading_bot.app.trade_logger import compute_stats
    stats = compute_stats()

    print("\n📊 Résumé Trading")
    print("------------------------")
    print(f"Trades gagnants : {stats['wins']}")
    print(f"Trades perdants : {stats['losses']}")
    print(f"Gains totaux : +{stats['profit']} USDT")
    print(f"Pertes totales : {stats['loss']} USDT")
    print(f"Profit net : {stats['total_pnl']} USDT")
    print(f"Taux de réussite : {stats['win_rate']}%")


def get_portfolio_value(ex: BinanceExchange, quote_asset='USDT', verbose=True):
    total_value = 0.0
    prices = {}
    details = []

    assets = ['USDT', 'BTC', 'ETH', 'BNB']

    for asset in assets:
        balance = ex.get_asset_balance(asset)
        if balance == 0:
            continue

        if asset == quote_asset:
            value = balance
        else:
            try:
                price = prices[asset] = ex.get_symbol_price(f'{asset}{quote_asset}')
                value = balance * price
            except:
                continue

        total_value += value
        details.append((asset, balance, round(value, 2)))

    if verbose:
        print("\n--- Détail du portefeuille ---")
        for asset, qty, value in details:
            print(f"{asset}: {qty} (≈ {value} {quote_asset})")

        print(f"\n💰 Valeur totale du portefeuille (en {quote_asset}): {round(total_value, 4)}")

    return round(total_value, 4)

if __name__ == "__main__":
    app()
