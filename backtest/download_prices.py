"""Baixa histórico diário dos principais ativos do playbook via yfinance
e salva em data/market_history.parquet (ou .json).
"""
import sys
from pathlib import Path
import yfinance as yf
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "SPX": "^GSPC",
    "NDX": "^IXIC",
    "RUT": "^RUT",
    "IBOV": "^BVSP",
    "WTI": "CL=F",
    "BRENT": "BZ=F",
    "OURO": "GC=F",
    "PRATA": "SI=F",
    "UST10Y": "^TNX",
    "UST30Y": "^TYX",
    "DXY": "DX-Y.NYB",
    "USDBRL": "USDBRL=X",
    "MARA": "MARA",
    "RIOT": "RIOT",
    "MSTR": "MSTR",
    "SGOV": "SGOV",  # proxy para rendimento de caixa em dólar
}

def main():
    print(f"Baixando histórico de {len(TICKERS)} ativos (2025-10-01 a 2026-11-03)...")
    dfs = {}
    for name, sym in TICKERS.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(start="2025-10-01", end="2026-11-03", interval="1d")
            if not h.empty:
                h = h.reset_index()
                # normalizar data
                date_col = "Date" if "Date" in h.columns else h.columns[0]
                h["date"] = pd.to_datetime(h[date_col]).dt.strftime("%Y-%m-%d")
                h = h[["date", "Open", "High", "Low", "Close", "Volume"]]
                h.columns = ["date", "open", "high", "low", "close", "volume"]
                h["ticker"] = name
                dfs[name] = h
                print(f"  [OK] {name} ({sym}): {len(h)} dias | Último: {h['date'].iloc[-1]} = {h['close'].iloc[-1]:.2f}")
            else:
                print(f"  [AVISO] {name} ({sym}): vazio")
        except Exception as e:
            print(f"  [ERRO] {name} ({sym}): {e}")

    if dfs:
        all_df = pd.concat(dfs.values(), ignore_index=True)
        out_path = DATA_DIR / "market_history.csv"
        all_df.to_csv(out_path, index=False, encoding="utf-8")
        print(f"\n[SUCESSO] {len(all_df)} registros salvos em {out_path}")

if __name__ == "__main__":
    main()
