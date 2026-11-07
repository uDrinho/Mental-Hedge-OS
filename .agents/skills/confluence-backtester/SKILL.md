---
name: confluence-backtester
description: >-
  Executa a suíte de backtesting histórico, mineração de confluências
  estatísticas e atualização de guardrails em trade_learning_memory.json.
  Use sempre que novas chamadas forem adicionadas em playbook/calls/ ou quando
  calibrar o motor de score em risk_advisor.py.
---

# Skill: Quantitative Confluence Backtester & Guardrail Auditor

Esta skill orienta a avaliação empírica (*Evals*) das chamadas extraídas pelos agentes contra séries temporais de mercado.

## 1. Pipeline de Auditoria Quantitativa

1. **Atualização e Verificação das Séries Históricas:**
   - Verifique se `backtest/data/market_history.csv` cobre a janela das chamadas em `playbook/calls/*.jsonl`. Caso necessário, execute `backtest/download_prices.py`.
2. **Execução do Replay Histórico (`backtest/run_backtest.py`):**
   - Cruza cada chamada direcional (`long` / `short`) com o fechamento do dia útil correspondente e calcula retornos em `7d`, `30d`, `60d`, ganho máximo favorável (`max_gain_pct`) e *drawdown* máximo adverso (`max_loss_pct`).
   - Gera `backtest/data/backtest_results.csv`.
3. **Mineração de Confluências (`backtest/mine_confluences.py`):**
   - Compara o DNA das operações vencedoras contra as perdedoras avaliando:
     - Tendência prévia de 5 dias do Dólar Global (`DXY`) e juros de 30 anos (`UST30Y`).
     - Diferença de assertividade entre `entrada` / `aumento` (gatilhos reais) vs `expectativa` (comentários narrativos).
     - Gatilhos verbais e padrões gráficos citados.
4. **Calibração de Guardrails (`trade_learning_memory.json` & `risk_advisor.py`):**
   - Sempre que uma classe de operação apresentar *drawdown* severo ou baixa assertividade sem proteção (ex: mineradoras sem hedge ou compras em topo de Onda 5), registre a autópsia em `trade_learning_memory.json` e ajuste os pesos dos 4 pilares em `risk_advisor.py`.

