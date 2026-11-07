---
name: chart-ocr-transcriber
description: >-
  Runbook multimodal para leitura e transcrição estruturada de gráficos técnicos
  do TradingView. Use quando precisar extrair níveis de suporte/resistência,
  caixas de liquidez, padrões gráficos (cunhas, pivôs, canais) e indicadores
  visuais de imagens financeiras sem alucinar valores.
---

# Skill: Chart OCR & Technical Pattern Transcriber

Esta skill orienta subagentes de visão na extração fiel de informações técnicas contidas em imagens de gráficos financeiros (TradingView, Koyfin, Bloomberg, etc.).

## 1. Elementos Obrigatórios na Leitura Visual

Ao inspecionar uma imagem de gráfico, extraia na seguinte ordem:

1. **Identificação do Ativo e Timeframe:**
   - Leia o cabeçalho superior esquerdo (ex: `BTCUSD · 1D`, `US30Y · 1W`, `WTI · 4H`, `TOTAL3 · 1D`).
   - Caso seja um gráfico duplo ou comparativo, separe a descrição em **Painel Esquerdo/Superior** e **Painel Direito/Inferior**.
2. **Preço Atual e Variação:**
   - Extraia o valor destacado no eixo direito (cotação atual) e a variação percentual se visível.
3. **Anotações Desenhadas pelo Autor (O Sinal Principal):**
   - **Caixas Verdes (Zonas de Demanda / Compra):** Anote o intervalo de preço superior e inferior da caixa.
   - **Caixas Vermelhas/Rosas (Zonas de Oferta / Venda / Stop):** Anote a faixa exata de resistência.
   - **Linhas Horizontais (Pivôs e Alvos):** Liste os preços marcados nas etiquetas laterais.
   - **Setas, Caminhos Projetados (Path Tool) e Textos no Gráfico:** Transcreva literalmente qualquer texto escrito sobre o canvas e a direção das setas desenhadas.
4. **Estrutura de Preço e Indicadores Secundários:**
   - Identifique se há cunha ascendente/descendente (*rising/falling wedge*), canal paralelo, divergência em RSI/CVD ou perfil de volume (*Volume Profile*).

## 2. Regras Anti-Alucinação Visual

- **Nunca estime valores fora do eixo:** Só reporte números de suporte/alvo se a etiqueta de preço no eixo Y ou na linha horizontal estiver legível. Se a resolução impedir a leitura exata do número, descreva a região aproximada indicando `[aprox.]`.
- **Não dê recomendação própria:** Limite-se a descrever objetivamente o que está desenhado no gráfico.

