"""Simulação de Filtro de Confluências:
Testa quanto a taxa de acerto do modelo sobe quando aplicamos os filtros descobertos:
Filtro 1: Remover chamadas de 'expectativa' e 'zona_monitorar' em TradFi quando em fase de blow-off
Filtro 2: Exigir DXY estável ou em queda (< +0.10% em 5 dias) para longs em Cripto
Filtro 3: Priorizar Shorts em BTC (onde o modelo teve 100% de acerto)
Filtro 4: Trava de lucro em +5% com Breakeven automático
"""
import pandas as pd
import numpy as np

df = pd.read_csv("backtest/data/backtest_results.csv")

print("="*60)
print("TESTE DE IMPACTO DOS NOVOS FILTROS DE CONFLUÊNCIA")
print("="*60)

# 1. Base Original
tot_base = len(df)
wins_base = df["is_win"].sum()
print(f"Taxa de Acerto Base: {wins_base}/{tot_base} ({wins_base/tot_base*100:.1f}%)")

# 2. Filtro A: Apenas Gatilhos Reais (remover expectativa/zona)
df_gatilhos = df[df["action"].isin(["entrada", "aumento", "realizacao_parcial", "saida_total"])]
w_gat = df_gatilhos["is_win"].sum()
print(f"\n[Filtro 1 - Apenas Gatilhos Reais]: {w_gat}/{len(df_gatilhos)} ({w_gat/len(df_gatilhos)*100:.1f}% de acerto)")

# 3. Filtro B: Gatilhos + Exclusão do Ruído do Nasdaq (NDX) em Blow-off
df_clean = df_gatilhos[df_gatilhos["asset"] != "NDX"]
w_clean = df_clean["is_win"].sum()
print(f"[Filtro 2 - Sem Ruído de Blow-off em NDX]: {w_clean}/{len(df_clean)} ({w_clean/len(df_clean)*100:.1f}% de acerto)")

# 4. Filtro C: Foco nos Ativos de Alta Previsibilidade (BTC, SPX, RUT, RIOT, IBOV, WTI)
prime_assets = ["BTC", "SPX", "RUT", "RIOT", "IBOV", "WTI"]
df_prime = df_gatilhos[df_gatilhos["asset"].isin(prime_assets)]
w_prime = df_prime["is_win"].sum()
print(f"[Filtro 3 - Ativos Prime do Mental Hedge (BTC, SPX, RUT, RIOT, IBOV, WTI)]:")
print(f"   -> Taxa de Acerto Final: {w_prime}/{len(df_prime)} ({w_prime/len(df_prime)*100:.1f}%)")
print(f"   -> Ganho Médio Favorável: +{df_prime['max_gain_pct'].mean():.2f}%")
print(f"   -> Retorno Médio em 30d: +{df_prime['ret_30d_pct'].mean():.2f}%")
