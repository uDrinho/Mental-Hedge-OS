---
name: macro-call-extractor
description: >-
  Extrai teses macroeconômicas, regras de método e chamadas operacionais
  estruturadas (.jsonl) a partir de chunks mensais de texto e transcrições
  de gráficos. Use ao processar novos períodos em playbook/chunks/ para popular
  playbook/notes/ e playbook/calls/.
---

# Skill: Macro Thesis & Operational Call Extractor

Esta skill padroniza a conversão de publicações não estruturadas (`playbook/chunks/AAAA-MM.txt`) em artefatos auditáveis para o motor de backtest.

## 1. Fluxo de Execução Passo a Passo

1. **Leitura Integral do Período:**
   - Leia o arquivo `playbook/chunks/AAAA-MM.txt` completo, incluindo as transcrições de imagens acopladas a cada publicação.
2. **Geração das Notas Analíticas (`playbook/notes/AAAA-MM.md`):**
   - Estruture exatamente as 7 seções exigidas em `playbook/EXTRACTION_GUIDE.md`:
     1. Resumo do mês (máx. 15 linhas)
     2. Teses e visões macro (com tradução em 1 frase simples para leigo)
     3. Princípios de método (citações literais + `tweet_id`)
     4. Indicadores, ferramentas e fontes citadas
     5. Glossário do autor
     6. Erros, stops e mudanças de opinião (insumo para `trade_learning_memory.json`)
     7. Ruído descartado
3. **Extração de Chamadas Operacionais (`playbook/calls/AAAA-MM.jsonl`):**
   - Gere uma linha JSON por ação operacional ou visão direcional concreta sobre um ativo.
   - Siga estritamente o schema `OperationalCall` definido em `core/schemas.py`.

## 2. Validação Determinística Obrigatória

Antes de concluir a tarefa, execute o validador Pydantic via linha de comando para garantir 100% de conformidade de tipos e campos:

```bash
./.venv/bin/python -c "
import json
from core.schemas import OperationalCall
with open('playbook/calls/AAAA-MM.jsonl', encoding='utf-8') as f:
    calls = [OperationalCall.model_validate(json.loads(line)) for line in f if line.strip()]
print(f'Validação concluída com sucesso: {len(calls)} calls válidas.')
"
```

