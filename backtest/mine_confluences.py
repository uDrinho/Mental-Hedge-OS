"""Mineração Profunda de Padrões e Confluências dos Trades Vencedores vs Perdedores.
Objetivo: Descobrir o 'DNA' dos 99 trades certos vs os 46 trades errados do Mental Hedge.
Cruza:
- Indicadores macro no momento do trade (DXY, Yield 30Y, Petróleo)
- Padrões visuais nos gráficos (TradingView, retângulos, timeframes)
- Notícias e sentimento da época (Pânico de capa, manchetes, Polymarket)
- Tipo de ação (Gatilho vs Zona vs Expectativa)
"""
import sys
import json
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

# Carrega os resultados do backtest e o histórico de preços
rdf = pd.read_csv("backtest/data/backtest_results.csv")
mkt = pd.read_csv("backtest/data/market_history.csv")
mkt["date"] = pd.to_datetime(mkt["date"])
piv = mkt.pivot(index="date", columns="ticker", values="close").sort_index()

print("="*60)
print(f"ANALISANDO O DNA DE {len(rdf)} TRADES ({rdf['is_win'].sum()} ACERTOS vs {(~rdf['is_win']).sum()} ERROS)")
print("="*60)

# Confluência 1: O que o DXY (Dólar Global) e os Yields (UST30Y) estavam fazendo?
wins_dxy_trend = []
loss_dxy_trend = []

for idx, row in rdf.iterrows():
    dt = pd.to_datetime(row["date"])
    sub_dxy = piv.loc[piv.index <= dt, "DXY"].dropna()
    sub_tyx = piv.loc[piv.index <= dt, "UST30Y"].dropna()
    
    if len(sub_dxy) >= 5 and len(sub_tyx) >= 5:
        # Tendência de 5 dias do DXY e UST30Y antes da entrada
        dxy_5d = (sub_dxy.iloc[-1] - sub_dxy.iloc[-5]) / sub_dxy.iloc[-5] * 100
        tyx_5d = (sub_tyx.iloc[-1] - sub_tyx.iloc[-5]) / sub_tyx.iloc[-5] * 100
        
        item = {
            "is_win": row["is_win"],
            "asset": row["asset"],
            "direction": row["direction"],
            "dxy_trend_5d": dxy_5d,
            "tyx_trend_5d": tyx_5d,
            "max_gain": row["max_gain_pct"],
            "ret_30d": row["ret_30d_pct"]
        }
        if row["is_win"]:
            wins_dxy_trend.append(item)
        else:
            loss_dxy_trend.append(item)

w_df = pd.DataFrame(wins_dxy_trend)
l_df = pd.DataFrame(loss_dxy_trend)

print("\n--- 1. CONFLUÊNCIA MACRO: DXY & JUROS (UST30Y) ---")
print(f"Trades Certos: DXY médio 5d antes do trade: {w_df['dxy_trend_5d'].mean():.2f}% | Yield 30Y: {w_df['tyx_trend_5d'].mean():.2f}%")
print(f"Trades Errados: DXY médio 5d antes do trade: {l_df['dxy_trend_5d'].mean():.2f}% | Yield 30Y: {l_df['tyx_trend_5d'].mean():.2f}%")

# Confluência 2: Relação Direção x Classe de Ativo
print("\n--- 2. MATRIZ DE CONFLUÊNCIA: ATIVO x DIREÇÃO (LONG vs SHORT) ---")
cross = pd.crosstab([rdf["asset"], rdf["direction"]], rdf["is_win"], normalize="index") * 100
counts = pd.crosstab([rdf["asset"], rdf["direction"]], rdf["is_win"])
summary_matrix = pd.concat([counts, cross[True].rename("Win_Rate_%")], axis=1)
print(summary_matrix.to_string())

# Confluência 3: Palavras-chave nas Citações dos Vencedores vs Perdedores
print("\n--- 3. PADRÕES DE LINGUAGEM DO AUTOR (GATILHOS VERBAIS) ---")
win_quotes = " ".join(rdf[rdf["is_win"]]["quote"].dropna().astype(str)).lower()
loss_quotes = " ".join(rdf[~rdf["is_win"]]["quote"].dropna().astype(str)).lower()

keywords = ["absorção", "estrutura", "0 a 0", "primeira mão", "pivots", "liquidez", "fundo", "topo", "cunha", "short", "long", "estranho", "delicado", "cuidado"]
print(f"{'Palavra-chave':<18} | {'Em Trades Certos (%)':<22} | {'Em Trades Errados (%)'}")
print("-" * 65)
for kw in keywords:
    c_win = win_quotes.count(kw)
    c_loss = loss_quotes.count(kw)
    tot = c_win + c_loss
    if tot > 0:
        p_win = (c_win / tot) * 100
        p_loss = (c_loss / tot) * 100
        print(f"{kw:<18} | {p_win:>20.1f}% | {p_loss:>19.1f}%")
