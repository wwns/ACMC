"""
Prosty logger: zapisuje na disk i do bazy danych (db.log_event)
Użycie: logger.info(...), logger.error(...)
"""
import logging
from logging.handlers import RotatingFileHandler
from db import log_event, init_db

LOG_PATH = 'acmc_app.log'

init_db()

logger = logging.getLogger('acmc')
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)


def info(msg: str):
    logger.info(msg)
    try:
        log_event('INFO', msg)
    except Exception:
        pass


def error(msg: str):
    logger.error(msg)
    try:
        log_event('ERROR', msg)
    except Exception:
        pass


def debug(msg: str):
    logger.debug(msg)
    try:
        log_event('DEBUG', msg)
    except Exception:
        pass
