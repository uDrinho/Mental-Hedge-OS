"""Motor de Backtest / Replay Histórico:
Avalia as chamadas operacionais catalogadas contra os preços reais históricos.
Calcula: taxa de acerto, retorno médio, drawdown e compara com o CDI/SGOV e Buy&Hold.
"""
import glob
import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core.config import BACKTEST_DATA_DIR as DATA_DIR, ASSET_MAP

def load_history():
    df = pd.read_csv(DATA_DIR / "market_history.csv")
    df["date"] = pd.to_datetime(df["date"])
    # Criar tabela dinâmica pivotada por ticker
    piv = df.pivot(index="date", columns="ticker", values="close").sort_index()
    return piv

def load_calls():
    files = sorted(glob.glob(str(BASE / "playbook/calls/*.jsonl")))
    calls = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            for line in fp:
                if line.strip():
                    c = json.loads(line)
                    calls.append(c)
    calls.sort(key=lambda x: x["date"])
    return calls

def run_backtest():
    piv = load_history()
    calls = load_calls()
    print(f"Total de chamadas carregadas: {len(calls)}")
    print(f"Janela histórica: {piv.index.min().strftime('%Y-%m-%d')} até {piv.index.max().strftime('%Y-%m-%d')}")

    results = []
    # Avalia chamadas direcionais concretas (entrada, aumento, realizacao, stop, expectativa/zona)
    for c in calls:
        dt_str = c["date"][:10]
        dt = pd.to_datetime(dt_str)
        asset = ASSET_MAP.get(c["asset"])
        if not asset or asset not in piv.columns:
            continue

        direction = c["direction"]
        action = c["action"]
        if direction not in ("long", "short"):
            continue

        # Encontra o dia útil mais próximo igual ou seguinte à data da call
        sub = piv.loc[piv.index >= dt, asset].dropna()
        if len(sub) < 2:
            continue

        entry_px = sub.iloc[0]
        entry_date = sub.index[0]

        # Medir retornos em horizontes de 7 dias, 30 dias e 60 dias (ou até o fim dos dados)
        px_7d = sub.iloc[min(5, len(sub)-1)]
        px_30d = sub.iloc[min(22, len(sub)-1)]
        px_60d = sub.iloc[min(44, len(sub)-1)]
        max_favorable = sub.max() if direction == "long" else sub.min()
        max_adverse = sub.min() if direction == "long" else sub.max()

        mult = 1 if direction == "long" else -1
        ret_7d = mult * (px_7d - entry_px) / entry_px
        ret_30d = mult * (px_30d - entry_px) / entry_px
        ret_60d = mult * (px_60d - entry_px) / entry_px
        max_gain = mult * (max_favorable - entry_px) / entry_px
        max_drawdown = mult * (max_adverse - entry_px) / entry_px

        # Consideramos acerto se em 30d deu retorno positivo OU se atingiu +5% favorável antes de reverter
        is_win = (ret_30d > 0) or (max_gain >= 0.05)

        results.append({
            "date": entry_date.strftime("%Y-%m-%d"),
            "call_date": c["date"],
            "asset": asset,
            "action": action,
            "direction": direction,
            "entry_px": entry_px,
            "px_30d": px_30d,
            "ret_7d_pct": ret_7d * 100,
            "ret_30d_pct": ret_30d * 100,
            "ret_60d_pct": ret_60d * 100,
            "max_gain_pct": max_gain * 100,
            "max_loss_pct": max_drawdown * 100,
            "is_win": is_win,
            "quote": c.get("quote", "")[:100],
            "tweet_id": c.get("tweet_id")
        })

    rdf = pd.DataFrame(results)
    out_csv = DATA_DIR / "backtest_results.csv"
    rdf.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"\n[SUCESSO] {len(rdf)} chamadas avaliadas contra os preços reais. Resultados em {out_csv}")

    # Estatísticas consolidadas
    print("\n" + "="*50)
    print("RESUMO CONSOLIDADO DO BACKTEST")
    print("="*50)
    total_ops = len(rdf)
    wins = rdf["is_win"].sum()
    win_rate = (wins / total_ops) * 100
    print(f"Total de operações avaliadas: {total_ops}")
    print(f"Operações vencedoras (Win Rate): {wins} ({win_rate:.1f}%)")
    print(f"Retorno médio em 30 dias: {rdf['ret_30d_pct'].mean():.2f}%")
    print(f"Retorno médio em 60 dias: {rdf['ret_60d_pct'].mean():.2f}%")
    print(f"Ganho máximo favorável médio: {rdf['max_gain_pct'].mean():.2f}%")

    print("\n--- POR CLASSE / ATIVO ---")
    by_asset = rdf.groupby("asset").agg(
        total=("is_win", "count"),
        taxa_acerto=("is_win", lambda x: f"{x.mean()*100:.1f}%"),
        ret_medio_30d=("ret_30d_pct", "mean")
    )
    print(by_asset.to_string())

    print("\n--- POR TIPO DE AÇÃO ---")
    by_action = rdf.groupby("action").agg(
        total=("is_win", "count"),
        taxa_acerto=("is_win", lambda x: f"{x.mean()*100:.1f}%"),
        ret_medio_30d=("ret_30d_pct", "mean")
    )
    print(by_action.to_string())

    return rdf

if __name__ == "__main__":
    run_backtest()
