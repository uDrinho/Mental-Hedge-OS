# Instruções de Extração — Playbook Mental Hedge (Fase 1)

Você vai ler UM mês de tweets do @mentalhedgebr (arquivo em `playbook/chunks/AAAA-MM.txt`)
e extrair o conhecimento dele de forma estruturada. O dono do projeto NÃO entende de economia:
tudo precisa ser fiel ao autor E explicado de forma simples.

## Regras de ouro (anti-alucinação)
1. **Só use o que está no arquivo.** Não complete com conhecimento próprio sobre o que "provavelmente" aconteceu no mercado.
2. **Toda afirmação precisa citar o `id` do tweet** de origem, ex: `(id 2117270000335814853)`.
3. Separe sempre **o que o autor disse** de **sua interpretação**. Interpretações vão marcadas com `[interpretação]`.
4. Se algo for ambíguo (ironia, meme, piada), marque `[ambíguo]` e não transforme em regra.
5. Respostas curtas a seguidores (RESPOSTA a @...) valem como fonte, mas com peso menor que POST/THREAD.
6. Não dê conselhos financeiros próprios. Você está documentando o método de outra pessoa.

## Saída 1 — `playbook/notes/AAAA-MM.md`
Seções, nesta ordem:

### 1. Resumo do mês (máx. 15 linhas)
Visão de mercado do autor naquele mês: em que fase do ciclo ele achava que estávamos, viés (comprado/vendido/caixa) por classe de ativo, e o que mudou desde o início do mês.

### 2. Teses e visões macro
Lista de teses (ciclo de 4 anos do BTC, juros/Treasuries, Fed, Japão/BoJ, petróleo, dólar/DXY, ouro, liquidez, IBOV/Brasil, S&P/Nasdaq, etc.).
Para cada uma: tese em 1–2 frases, ativos afetados, ids, e "em linguagem simples" (1 frase para leigo).

### 3. Princípios de método (as REGRAS dele)
Frases que revelam como ele decide: ex. "expectativa não é entrada", entrada em 3 mãos, "sem estrutura sem short",
zonas de liquidez, stop no 0 a 0, position vs. trade, sentimento contrário, gestão de risco, quando ficar em caixa.
Cite trecho literal curto entre aspas + id. Agrupe por tema.

### 4. Indicadores, ferramentas e fontes que ele usa
Indicadores (funding, FOMO/medo, curva de juros, CPI, payroll, Truflation, Polymarket/Kalshi...), timeframes,
e perfis/portais que ele cita como fonte (com a forma como ele os usa: confia, ironiza, contrapõe).

### 5. Glossário do autor
Termos/jargões dele (ex: "estrutura", "1ª mão", "distribuição de topo", "blow off", "zona", "absorção", "pivots", "0 a 0")
com definição simples, inferida do contexto + id de exemplo. Marque `[interpretação]` quando inferido.

### 6. Erros, stops e mudanças de opinião
Onde ele admitiu erro, foi stopado, mudou de visão ou invalidou uma tese. Isso é ouro para o aprendizado da IA.

### 7. Ruído (não usar como regra)
Lista curta de temas fora do método (política, piadas, polêmicas) — apenas para registro, 1 linha cada.

## Saída 2 — `playbook/calls/AAAA-MM.jsonl`
UMA linha JSON por ação/opinião operacional concreta sobre um ativo (é a base do futuro backtest). Campos:

```json
{"date": "2026-11-02T14:57", "tweet_id": "2117270000335814853", "asset": "WTI/Brent",
 "action": "entrada", "direction": "short", "horizon": "trade",
 "hand": "1/3", "levels": {"zone": [106, 111.5], "entry": null, "stop": null, "targets": []},
 "condition": "o que ele disse que precisava acontecer (se houver)",
 "quote": "trecho literal curto", "refs": ["ids de tweets anteriores citados"],
 "source_type": "post|thread|resposta|imagem"}
```

Valores de `action`: `expectativa` (cenário esperado, sem posição), `zona_monitorar` (preço chegou/está perto da região de interesse),
`aguardando_confirmacao`, `entrada`, `aumento`, `realizacao_parcial`, `saida_total`, `stop`, `invalidacao`, `manutencao` (reafirma posição), `alerta_risco`.
`direction`: `long`, `short`, `neutro`, `caixa`. `horizon`: `trade`, `position`, `indefinido`.
Use `null` para níveis não informados — **nunca invente número**. Níveis podem vir das transcrições de IMAGEM (cite em `source_type: "imagem"`).
Ativos com nome padronizado: `BTC`, `ETH`, `SOL`, `ALTS`, `TOTAL` (market cap cripto), `SPX`, `NDX`, `IBOV`, `DXY`, `USDBRL`, `OURO`, `PRATA`, `WTI/Brent`, `UST10Y`, `UST30Y`, `JGB`, `EWZ`, ou o ticker citado.

## Ao terminar
Valide que o `.jsonl` tem uma linha JSON válida por linha (rode um `python -c` simples com `.\.venv\Scripts\python.exe`).
Responda ao agente pai com: nº de calls extraídas, 3 principais teses do mês, e qualquer problema de dados notado (ex.: dias faltando).
