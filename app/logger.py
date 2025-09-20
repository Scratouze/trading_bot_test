import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(level: str = 'INFO', file_path: str = 'logs/bot.log') -> logging.Logger:
    """Configure et retourne un logger rotatif."""
    # Crée le dossier si nécessaire
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger('firstapp')
    logger.setLevel(level)
    # Ne pas dupliquer les handlers si déjà configuré
    if logger.handlers:
        return logger
    fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s', '%Y-%m-%d %H:%M:%S')
    fh = RotatingFileHandler(file_path, maxBytes=2_000_000, backupCount=5)
    fh.setFormatter(fmt)
    fh.setLevel(level)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.setLevel(level)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger