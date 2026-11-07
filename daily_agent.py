"""Agente Autônomo Diário (Mental Hedge Daily Runner v2.0).
Executa o ciclo diário completo de inteligência:
1. Puxa cotações atualizadas e tendências de confluência (BTC, ETH, SPX, NDX, RUT, WTI, UST30Y, DXY, USDBRL).
2. Atualiza rendimentos de Caixa Seguro (SGOV e Selic) e grava snapshot da curva de capital.
3. Avalia posições abertas na carteira simulada contra as regras de Breakeven (+5%) e Stops.
4. Cruza o mercado com as Regras Anti-Ruína (trade_learning_memory.json) e Confluências Estatísticas.
5. Gera o Briefing do Dia no padrão leigo obrigatório ("O que aconteceu -> Por que importa -> O que fazer").
6. Dispara o Briefing e Alertas diretamente para o Telegram e atualiza o Dashboard.
"""
import json
import datetime
import sys
from pathlib import Path
import yfinance as yf
from paper_trader import (
    get_portfolio_summary,
    get_connection,
    record_daily_snapshot,
    evaluate_breakeven_and_exits
)
from telegram_notifier import broadcast_daily_briefing, send_telegram_message

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
MEMORY_PATH = BASE_DIR / "trade_learning_memory.json"
BRIEFING_OUT = BASE_DIR / "daily_briefing.json"

TICKERS_WATCH = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SPX": "^GSPC",
    "NDX": "^NDX",
    "RUT": "^RUT",
    "WTI": "CL=F",
    "UST30Y": "^TYX",
    "DXY": "DX-Y.NYB",
    "USDBRL": "USDBRL=X"
}

def load_learning_rules():
    if MEMORY_PATH.exists():
        try:
            return json.load(open(MEMORY_PATH, encoding="utf-8")).get("hard_rules", [])
        except Exception:
            pass
    return []

def fetch_live_market_snapshot():
    snapshot = {}
    print("[1/5] Coletando cotações e confluências de mercado via yfinance...")
    for sym, ticker in TICKERS_WATCH.items():
        try:
            t = yf.Ticker(ticker)
            h = t.history(period="7d")
            if not h.empty:
                px = float(h["Close"].iloc[-1])
                prev = float(h["Close"].iloc[-2]) if len(h) > 1 else px
                var_1d = ((px - prev) / prev * 100) if prev else 0.0
                
                # Variação de 5 dias (confluência de fluxo macro)
                px_5d = float(h["Close"].iloc[0]) if len(h) >= 5 else prev
                var_5d = ((px - px_5d) / px_5d * 100) if px_5d else 0.0
                
                snapshot[sym] = {
                    "price": round(px, 2),
                    "variation_pct": round(var_1d, 2),
                    "variation_5d_pct": round(var_5d, 2)
                }
            else:
                snapshot[sym] = {"price": 0.0, "variation_pct": 0.0, "variation_5d_pct": 0.0}
            print(f"  - {sym}: {snapshot[sym]['price']} (1D: {snapshot[sym]['variation_pct']}%, 5D: {snapshot[sym].get('variation_5d_pct', 0)}%)")
        except Exception as e:
            snapshot[sym] = {"price": 0.0, "variation_pct": 0.0, "variation_5d_pct": 0.0, "error": str(e)}
    return snapshot

def update_daily_cash_yield():
    print("[2/5] Atualizando rendimento diário de Caixa Seguro (SGOV e Selic)...")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio WHERE id = 1")
        port = dict(cursor.fetchone())
        
        sgov_yield = port.get("sgov_yield_daily", 0.000186)
        selic_yield = port.get("selic_yield_daily", 0.000404)
        
        earned_usd = port["cash_usd"] * sgov_yield
        earned_brl = port["cash_brl"] * selic_yield
        
        new_usd = port["cash_usd"] + earned_usd
        new_brl = port["cash_brl"] + earned_brl
        now = datetime.datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE portfolio 
            SET cash_usd = ?, cash_brl = ?, updated_at = ?
            WHERE id = 1
        """, (new_usd, new_brl, now))
        conn.commit()
        print(f"  [OK] Caixa rendeu hoje: +US$ {earned_usd:.2f} (SGOV) e +R$ {earned_brl:.2f} (Selic)")
        
        # Grava snapshot na curva de capital histórica
        record_daily_snapshot(daily_yield_usd=earned_usd, daily_yield_brl=earned_brl)
        return earned_usd, earned_brl

def generate_daily_briefing(market_data):
    print("[3/5] Gerando Briefing com Filtros de Confluência e Regras Anti-Ruína...")
    port = get_portfolio_summary()
    rules = load_learning_rules()
    
    # Preços e tendências
    btc = market_data.get("BTC", {})
    eth = market_data.get("ETH", {})
    spx = market_data.get("SPX", {})
    ndx = market_data.get("NDX", {})
    wti = market_data.get("WTI", {})
    tyx = market_data.get("UST30Y", {})
    dxy = market_data.get("DXY", {})
    
    btc_px = btc.get("price", 0)
    eth_px = eth.get("price", 0)
    spx_px = spx.get("price", 0)
    wti_px = wti.get("price", 0)
    tyx_px = tyx.get("price", 0)
    dxy_px = dxy.get("price", 0)
    dxy_5d = dxy.get("variation_5d_pct", 0.0)

    insights = []
    
    # 1. Filtro Confluência DXY (Dólar Global)
    if dxy_5d > 0.3:
        insights.append(
            f"💵 **Dólar Global Forte (DXY a {dxy_px}, +{dxy_5d}% em 5d)**\n"
            f"• *O que aconteceu*: O índice do dólar mundial acelerou para cima nos últimos dias.\n"
            f"• *Por que importa*: Confluência Estatística #2 provou que abrir compras em cripto com DXY subindo derruba o acerto para menos de 50% (o dólar forte age como um aspirador de liquidez global).\n"
            f"• *O que fazer*: **TRAVA ATIVA: Proibido abrir novas compras (longs) em Cripto** enquanto o DXY não estabilizar."
        )
    else:
        insights.append(
            f"💵 **Dólar Global Controlado (DXY a {dxy_px})**\n"
            f"• *O que aconteceu*: O índice DXY está calmo e sem disparada agressiva.\n"
            f"• *Por que importa*: Abre janela segura de liquidez internacional para ativos de risco.\n"
            f"• *O que fazer*: Sinal neutro/positivo para monitorar suportes em TradFi e Cripto."
        )

    # 2. Bolsas EUA (SPX / NDX) & Regra Anti-Blowoff
    if spx_px > 6800 or ndx.get("price", 0) > 23000:
        insights.append(
            f"🇺🇸 **Bolsas dos EUA em Fase Euforia (S&P 500: {spx_px:,.0f} | Nasdaq: {ndx.get('price', 0):,.0f})**\n"
            f"• *O que aconteceu*: As bolsas americanas seguem esticadas no final de ciclo (Onda 5 parabólica).\n"
            f"• *Por que importa*: Regra Canônica `RULE_NEVER_SHORT_BLOWOFF`. Irracionalidade de euforia não tem teto prévio; tentar shortear no meio da subida gera ruína.\n"
            f"• *O que fazer*: **Manter 100% dos recursos fora de risco em SGOV**. Deixar a bolha inflar e aguardar topo duplo/reversão clara."
        )

    # 3. Petróleo WTI & Posição Estrutural Short
    if wti_px > 90:
        insights.append(
            f"🛢️ **Petróleo WTI (US$ {wti_px:,.2f}) — Zona de Resistência Macro**\n"
            f"• *O que aconteceu*: O barril está na grande caixa de oferta entre US$ 95 e US$ 111.\n"
            f"• *Por que importa*: Conforme nossa pesquisa macro, a tese secular do Mental Hedge aponta para alvos sub-US$ 50 e sub-US$ 30.\n"
            f"• *O que fazer*: Manter o Position Short ativo em 1ª mão. Caso o preço perca o suporte imediato, adicionar a 2ª mão."
        )

    # 4. Cripto: Fila de Rotação (BTC -> ETH -> Alts)
    if btc_px:
        eth_ath = 4957.0
        insights.append(
            f"₿ **Criptoativos (BTC: US$ {btc_px:,.0f} | ETH: US$ {eth_px:,.0f})**\n"
            f"• *O que aconteceu*: O Bitcoin consolida sua estrutura e o Ethereum negocia abaixo de US$ {eth_ath:,.0f}.\n"
            f"• *Por que importa*: Regra `RULE_ETH_PREREQUISITE_FOR_ALTS`. O transbordo institucional genuíno para Altcoins só é liberado após o ETH romper sua máxima histórica.\n"
            f"• *O que fazer*: **Manter no máximo 4% do patrimônio em alts táticas** (4 compras de 1% em compressão). Reservar os outros 80% em caixa SGOV."
        )

    # 5. Caixa Seguro & Gestão Anti-Ruína
    insights.append(
        f"🛡️ **Proteção Ativa de Capital (Anti-Ruína)**\n"
        f"• *O que aconteceu*: Saldo total protegido em **US$ {port['total_portfolio_usd']:,.2f}** (US$ {port['cash_usd']:,.2f} em SGOV e R$ {port['cash_brl']:,.2f} no Tesouro Selic).\n"
        f"• *Por que importa*: Caixa remunerado em dólar e real não é dinheiro parado; é arma estratégica para comprar na capitulação quando todos estiverem em pânico.\n"
        f"• *O que fazer*: Paciência absoluta. Seguir rendendo juros até os gatilhos confirmados de 3 mãos."
    )

    briefing = {
        "date": datetime.date.today().isoformat(),
        "generated_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "headline": "Briefing Macroeconômico — Mental Hedge Intelligence",
        "market_snapshot": market_data,
        "portfolio_status": port,
        "insights_leigos": insights,
        "active_rules_count": len(rules)
    }

    json.dump(briefing, open(BRIEFING_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] Briefing salvo em {BRIEFING_OUT}")
    return briefing

def run_daily_cycle(send_telegram: bool = True):
    print("="*65)
    print("INICIANDO CICLO DIÁRIO DE INTELIGÊNCIA MENTAL HEDGE (v2.0)")
    print("="*65)
    
    # 1. Coleta cotações
    market_data = fetch_live_market_snapshot()
    
    # 2. Atualiza rendimentos do Caixa
    update_daily_cash_yield()
    
    # 3. Avalia posições abertas (Stops e Breakevens)
    current_prices = {k: v.get("price", 0.0) for k, v in market_data.items() if v.get("price")}
    trade_events = evaluate_breakeven_and_exits(current_prices)
    if trade_events:
        print("[AVALIAÇÃO DE TRADES]:")
        for ev in trade_events:
            print(f"  {ev}")
            if send_telegram:
                send_telegram_message(ev)
                
    # 4. Gera Briefing Diário
    briefing = generate_daily_briefing(market_data)
    
    # 5. Dispara para o Telegram
    if send_telegram:
        print("[4/5] Disparando Briefing Diário para o canal do Telegram...")
        success = broadcast_daily_briefing()
        if success:
            print("  [OK] Mensagem entregue com sucesso ao seu Telegram!")
        else:
            print("  [AVISO] Telegram desligado ou não configurado.")
            
    print("\n" + "="*65)
    print("RESUMO LEIGO GERADO:")
    for ins in briefing["insights_leigos"]:
        print(f"\n{ins}")
    print("="*65)
    print("[5/5] Ciclo diário concluído com total integridade!")
    return briefing

if __name__ == "__main__":
    run_daily_cycle(send_telegram=True)
