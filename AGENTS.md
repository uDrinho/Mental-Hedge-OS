# AGENTS.md — Diretrizes de Engenharia e Operação de Agentes

Este documento define o contexto arquitetural, os contratos de dados, os *guardrails* determinísticos e os fluxos de validação para qualquer agente de IA (ou desenvolvedor) que atue neste repositório.

---

## 1. Visão Geral da Arquitetura Híbrida

O **Mental Hedge OS** separa estritamente a **extração semântica/visual via LLMs** da **validação quantitativa e gestão de risco determinística**:

- **Agentes nunca tomam decisões de alocação em voo livre:** Toda chamada extraída por subagentes em `playbook/calls/*.jsonl` é auditada contra séries temporais reais em `backtest/run_backtest.py` e filtrada pelas regras duras de `trade_learning_memory.json`.
- **Fonte Única de Verdade (`core/`):** Caminhos, constantes de risco (`ETH_ATH_USD`, `BREAKEVEN_TRIGGER_PCT`, `ASSET_MAP`) e modelos de validação (`Pydantic`) residem em `core/config.py` e `core/schemas.py`.
- **Tradução Acessível Obrigatória:** Qualquer relatório ou briefing gerado para o usuário final (`daily_agent.py`, `risk_advisor.py`, `telegram_notifier.py`) deve traduzir conceitos macroeconômicos em português claro seguindo a estrutura: **"O que aconteceu -> Por que importa -> O que fazer"**.

---

## 2. Skills Disponíveis no Repositório (`.agents/skills/`)

Os fluxos especializados de múltiplos passos estão empacotados como *Skills* sob demanda em `.agents/skills/`:

1. **`chart-ocr-transcriber`** (`.agents/skills/chart-ocr-transcriber/SKILL.md`):
   - *Quando usar:* Para transcrever gráficos técnicos do TradingView (identificação de par/ticker, timeframe, caixas verdes de suporte, caixas vermelhas de oferta, cunhas, médias móveis e níveis de preço explícitos).
2. **`macro-call-extractor`** (`.agents/skills/macro-call-extractor/SKILL.md`):
   - *Quando usar:* Para processar lotes mensais de publicações (`playbook/chunks/AAAA-MM.txt`) e gerar notas analíticas (`playbook/notes/AAAA-MM.md`) e chamadas operacionais estruturadas (`playbook/calls/AAAA-MM.jsonl`).
3. **`confluence-backtester`** (`.agents/skills/confluence-backtester/SKILL.md`):
   - *Quando usar:* Após adicionar novas chamadas ou atualizar dados de mercado, para rodar o motor de backtest, recalcular confluências estatísticas e atualizar a memória episódica de erros.

---

## 3. Regras de Ouro (Anti-Alucinação & Segurança)

1. **Rastreabilidade Obrigatória:** Toda afirmação em `playbook/notes/*.md` e todo registro em `playbook/calls/*.jsonl` deve conter o `tweet_id` exato de origem. Nunca invente níveis numéricos (`entry`, `stop`, `targets`) que não estejam explícitos no texto ou no gráfico transcrito (use `null`).
2. **Validação de Schema (`Pydantic`):** Nenhum arquivo `.jsonl` pode ser salvo sem antes passar pela validação do modelo `OperationalCall` definido em `core/schemas.py`.
3. **Preservação de Regras Duras (`trade_learning_memory.json`):** Nunca remova travas como `RULE_NO_MINER_WITHOUT_HEDGE`, `RULE_NO_TRADE_ON_MERE_EXPECTATION`, `RULE_ETH_PREREQUISITE_FOR_ALTS` ou `RULE_NEVER_SHORT_BLOWOFF`.
4. **Governança de Dados:** Nunca remova `telegram_config.json`, `browser_session/`, `images/` ou `tweets_raw.json` do `.gitignore`.

---

## 4. Comandos de Verificação e Testes

Antes de finalizar qualquer alteração de código ou extração de dados, execute a suíte de validação:

```bash
# Executar a suíte de testes unitários e validação de schemas
./.venv/bin/python -m unittest discover -s tests -v

# Recalcular backtest e matriz de confluências
./.venv/bin/python backtest/run_backtest.py
./.venv/bin/python backtest/mine_confluences.py
```

