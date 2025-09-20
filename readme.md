# Trading Bot (intégration CopilotPC)

Ce dossier contient un bot de trading simple basé sur un croisement de moyennes mobiles (SMA). Il est conçu pour être intégré à **CopilotPC** afin qu'un agent puisse lancer le bot via la fonction `run_app`.

## Installation (dans le repo Copilot)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r trading_bot/requirements.txt
Copy-Item trading_bot/.env.example .env
```

Ouvre ensuite `.env` et renseigne tes clés API Binance Testnet. Laisse `DRY_RUN=true` pour éviter tout ordre réel.

## Lancer le bot en local (mode dry-run + Testnet)

```powershell
python trading_bot/cli.py start
```

Le bot tournera en boucle et enregistrera les logs dans `trading_bot/logs/bot.log`.
