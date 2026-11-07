"""Módulo de Comunicação com o Telegram.
Envia automaticamente:
- O Briefing Diário em Português Claro
- Alertas imediatos de ativos entrando na Zona ou disparando Gatilhos
- Status da carteira de Paper Trading

Para ativar:
1. Obtenha um Token de bot com o @BotFather no Telegram.
2. Descubra seu Chat ID com o @userinfobot.
3. Configure o arquivo telegram_config.json
"""
import json
import urllib.request
import urllib.parse
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from risk_advisor import get_confluence_leaderboard
except Exception:
    get_confluence_leaderboard = None

CONFIG_PATH = BASE_DIR / "telegram_config.json"
BRIEFING_PATH = BASE_DIR / "daily_briefing.json"

def load_telegram_config():
    if CONFIG_PATH.exists():
        try:
            return json.load(open(CONFIG_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {
        "bot_token": "COLOQUE_SEU_TOKEN_AQUI",
        "chat_id": "COLOQUE_SEU_CHAT_ID_AQUI",
        "enabled": False
    }

def send_telegram_message(text: str):
    config = load_telegram_config()
    if not config.get("enabled") or "COLOQUE" in config.get("bot_token", ""):
        print("[AVISO] Telegram ainda não configurado ou desabilitado em telegram_config.json")
        return False

    token = config["bot_token"]
    chat_id = config["chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[ERRO] Falha ao enviar mensagem no Telegram: {e}")
        return False

def broadcast_daily_briefing():
    if not BRIEFING_PATH.exists():
        print("[ERRO] Arquivo daily_briefing.json não encontrado.")
        return False

    b = json.load(open(BRIEFING_PATH, encoding="utf-8"))
    port = b.get("portfolio_status", {})
    
    lines = [
        f"🧭 *{b.get('headline', 'Briefing Diário — Mental Hedge')}*",
        f"📅 _{b.get('generated_at')}_",
        "",
        "📊 *COTAÇÕES DE FECHAMENTO:*",
        f"• Bitcoin: `US$ {b['market_snapshot']['BTC']['price']:,.2f}` ({b['market_snapshot']['BTC']['variation_pct']}%)",
        f"• S&P 500: `US$ {b['market_snapshot']['SPX']['price']:,.2f}` ({b['market_snapshot']['SPX']['variation_pct']}%)",
        f"• Petróleo WTI: `US$ {b['market_snapshot']['WTI']['price']:,.2f}` ({b['market_snapshot']['WTI']['variation_pct']}%)",
        f"• Dólar / Real: `R$ {b['market_snapshot']['USDBRL']['price']:,.2f}`",
        "",
        "💡 *INSIGHTS & DISCIPLINA DO DIA:*",
    ]
    for ins in b.get("insights_leigos", []):
        lines.append(f"• {ins}")
        
    # Anexa o Leaderboard de Oportunidades & Assimetria
    if get_confluence_leaderboard:
        try:
            board = get_confluence_leaderboard(b.get("market_snapshot", {}))
            lines.extend([
                "",
                "🏆 *LEADERBOARD DE CONFLUÊNCIA & ASSIMETRIA:*"
            ])
            for item in board:
                lines.append(
                    f"{item['status_icon']} *{item['rank']}º {item['asset']} {item['direction'].upper()}*: `{item['score']}/100` — {item['summary']}"
                )
        except Exception as e:
            print(f"[AVISO] Não foi possível anexar leaderboard: {e}")

    lines.extend([
        "",
        "🛡️ *CARTEIRA HIPOTÉTICA:*",
        f"• Caixa em Dólar (SGOV): `US$ {port.get('cash_usd', 0):,.2f}`",
        f"• Caixa em Real (Selic): `R$ {port.get('cash_brl', 0):,.2f}`",
        f"• Posições Abertas: `{port.get('active_positions_count', 0)}`",
        "",
        "🔗 _Acesse o painel completo no seu computador: http://127.0.0.1:8000_"
    ])
    
    msg = "\n".join(lines)
    return send_telegram_message(msg)

if __name__ == "__main__":
    broadcast_daily_briefing()
