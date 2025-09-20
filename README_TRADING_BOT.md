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

## Intégration CopilotPC

Pour permettre à ton agent CopilotPC de lancer le bot, ajoute l'entrée suivante dans `config.toml` du serveur :

```toml
[run.allowlist]
trading_bot = ["C:\\chemin\\vers\\repo\\.venv\\Scripts\\python.exe", "trading_bot/cli.py", "start"]
```

Adapte `C:\chemin\vers\repo` au chemin réel où se trouve le dossier. Après redémarrage du serveur, l'agent pourra lancer le bot en appelant `run_app(name="trading_bot")`.

⚠️ Ne jamais commiter le fichier `.env` contenant tes clés API. Commence en **Testnet** et vérifie bien les montants d'ordre avant de désactiver `DRY_RUN`.