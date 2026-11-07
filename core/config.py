"""Configurações centralizadas, constantes de risco e mapeamento de ativos."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PLAYBOOK_DIR = BASE_DIR / "playbook"
CALLS_DIR = PLAYBOOK_DIR / "calls"
NOTES_DIR = PLAYBOOK_DIR / "notes"
BACKTEST_DATA_DIR = BASE_DIR / "backtest" / "data"

MEMORY_PATH = BASE_DIR / "trade_learning_memory.json"
BRIEFING_PATH = BASE_DIR / "daily_briefing.json"
TELEGRAM_CONFIG_PATH = BASE_DIR / "telegram_config.json"
PORTFOLIO_DB_PATH = BASE_DIR / "paper_portfolio.db"

# Parâmetros Canônicos Anti-Ruína
ETH_ATH_USD = 4957.0
BREAKEVEN_TRIGGER_PCT = 5.0
MAX_ALTS_ALLOCATION_PCT = 4.0
SAFE_CASH_TARGET_PCT = 80.0

# Tickers monitorados via Yahoo Finance (yfinance)
TICKERS_WATCH = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SPX": "^GSPC",
    "NDX": "^NDX",
    "RUT": "^RUT",
    "WTI": "CL=F",
    "UST30Y": "^TYX",
    "DXY": "DX-Y.NYB",
    "USDBRL": "USDBRL=X",
}

# Normalização de nomes de ativos extraídos pelos agentes para tickers das séries históricas
ASSET_MAP = {
    "BTC": "BTC",
    "ETH": "ETH",
    "SOL": "SOL",
    "SPX": "SPX",
    "NDX": "NDX",
    "RUT": "RUT",
    "IBOV": "IBOV",
    "WTI/Brent": "WTI",
    "WTI": "WTI",
    "Brent": "BRENT",
    "OURO": "OURO",
    "PRATA": "PRATA",
    "UST10Y": "UST10Y",
    "UST30Y": "UST30Y",
    "DXY": "DXY",
    "USDBRL": "USDBRL",
    "MARA": "MARA",
    "RIOT": "RIOT",
    "MSTR": "MSTR",
}

