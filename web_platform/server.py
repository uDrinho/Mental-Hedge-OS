"""Backend FastAPI para o Dashboard Mental Hedge.
Fornece APIs para:
- Briefing do Dia e Termômetro de Ciclo
- Radar de Teses (Expectativa vs Zona vs Gatilho)
- Carteira Hipotética de Paper Trading (Simulação, Curva de Capital e Posições)
- Feed de Tweets Recentes e Transcrições Gráficas
- Bíblia e Regras Operacionais do Playbook
- Disparo manual do Ciclo Diário e Notificação Telegram
"""
import json
import glob
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import sys

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from paper_trader import get_portfolio_summary, open_hand_position, evaluate_breakeven_and_exits
from daily_agent import run_daily_cycle
from risk_advisor import evaluate_investment_thesis, get_confluence_leaderboard

app = FastAPI(title="Mental Hedge Intelligence Dashboard")

# Serve arquivos estáticos (HTML/CSS/JS)
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def get_recent_tweets():
    dump_file = BASE / "mentalhedgebr_1_ano_tweets.json"
    if dump_file.exists():
        try:
            data = json.load(open(dump_file, encoding="utf-8"))
            return data[:50]
        except Exception:
            pass
    # Fallback para clones do GitHub sem o dump bruto (usa os metadados estruturados em playbook/calls/)
    try:
        files = sorted(glob.glob(str(BASE / "playbook/calls/*.jsonl")), reverse=True)
        items = []
        for f in files:
            for line in open(f, encoding="utf-8"):
                if line.strip():
                    c = json.loads(line)
                    items.append({
                        "id": c.get("tweet_id", ""),
                        "created_at_iso": c.get("date", ""),
                        "text": f"[{c.get('asset')} - {c.get('action').upper()}] {c.get('quote', '')}",
                        "metrics": {"likes": 0},
                        "image_transcriptions": [{"transcription": c.get("condition", "")}] if c.get("source_type") == "imagem" and c.get("condition") else []
                    })
                    if len(items) >= 30:
                        return items
        return items
    except Exception:
        return []

def get_backtest_stats():
    try:
        csv_path = BASE / "backtest/data/backtest_results.csv"
        df = pd.read_csv(csv_path)
        total = len(df)
        wins = int(df["is_win"].sum())
        win_rate = round((wins / total) * 100, 1)
        avg_30d = round(df["ret_30d_pct"].mean(), 2)
        avg_gain = round(df["max_gain_pct"].mean(), 2)
        
        by_asset = []
        for asset, grp in df.groupby("asset"):
            a_total = len(grp)
            a_wins = int(grp["is_win"].sum())
            by_asset.append({
                "asset": asset,
                "total": a_total,
                "wins": a_wins,
                "win_rate": round((a_wins / a_total) * 100, 1),
                "avg_30d": round(grp["ret_30d_pct"].mean(), 2)
            })
        by_asset.sort(key=lambda x: x["total"], reverse=True)

        return {
            "total_trades": total,
            "wins": wins,
            "win_rate": win_rate,
            "avg_ret_30d": avg_30d,
            "avg_max_gain": avg_gain,
            "by_asset": by_asset
        }
    except Exception as e:
        return {"error": str(e)}

def get_radar_theses():
    files = sorted(glob.glob(str(BASE / "playbook/calls/*.jsonl")), reverse=True)
    radar = {
        "expectativa": [],
        "zona_monitorar": [],
        "gatilho_entrada": []
    }
    seen = set()
    for f in files:
        for line in open(f, encoding="utf-8"):
            if not line.strip():
                continue
            c = json.loads(line)
            key = (c["asset"], c["action"], c["direction"])
            if key in seen:
                continue
            seen.add(key)
            
            item = {
                "date": c["date"][:10],
                "asset": c["asset"],
                "direction": c["direction"],
                "action": c["action"],
                "horizon": c["horizon"],
                "quote": c.get("quote", ""),
                "levels": c.get("levels", {})
            }
            if c["action"] in ("entrada", "aumento"):
                radar["gatilho_entrada"].append(item)
            elif c["action"] in ("zona_monitorar", "aguardando_confirmacao"):
                radar["zona_monitorar"].append(item)
            elif c["action"] in ("expectativa", "alerta_risco"):
                radar["expectativa"].append(item)
    return radar

@app.get("/api/summary")
def api_summary():
    stats = get_backtest_stats()
    briefing = {}
    briefing_file = BASE / "daily_briefing.json"
    if briefing_file.exists():
        try:
            briefing = json.load(open(briefing_file, encoding="utf-8"))
        except Exception:
            pass

    return {
        "cycle_stage": "Distribuição de Topo em TradFi & Início de Position Short (Petróleo / Juros)",
        "current_focus": "Preservação em Caixa (SGOV/Selic) + Shorts Macroestruturais (WTI e UST30Y)",
        "rotation_order": ["TradFi (Distribuição)", "BTC (Standby)", "ETH (Compra fatiada)", "Alts (Aguardando ETH ATH)"],
        "cash_allocation": {
            "cash_dollar_sgov": 65,
            "cash_brl_selic": 15,
            "active_positions": 20
        },
        "daily_briefing": briefing,
        "backtest_stats": stats,
        "leaderboard": get_confluence_leaderboard(briefing.get("market_snapshot", {}))
    }

@app.get("/api/portfolio")
def api_portfolio():
    return get_portfolio_summary()

@app.get("/api/advisory")
def api_advisory(asset: str = "BTC", direction: str = "long"):
    briefing_file = BASE / "daily_briefing.json"
    snapshot = {}
    if briefing_file.exists():
        try:
            b = json.load(open(briefing_file, encoding="utf-8"))
            snapshot = b.get("market_snapshot", {})
        except Exception:
            pass
    return evaluate_investment_thesis(asset, direction, snapshot)

@app.get("/api/leaderboard")
def api_leaderboard():
    briefing_file = BASE / "daily_briefing.json"
    snapshot = {}
    if briefing_file.exists():
        try:
            b = json.load(open(briefing_file, encoding="utf-8"))
            snapshot = b.get("market_snapshot", {})
        except Exception:
            pass
    return get_confluence_leaderboard(snapshot)

@app.get("/api/radar")
def api_radar():
    return get_radar_theses()

@app.get("/api/tweets")
def api_tweets():
    return get_recent_tweets()

@app.get("/api/playbook")
def api_playbook():
    pb_file = BASE / "playbook/PLAYBOOK_MENTAL_HEDGE.md"
    content = ""
    if pb_file.exists():
        content = pb_file.read_text(encoding="utf-8")
    return {"content": content}

@app.post("/api/run_cycle")
def api_run_cycle():
    try:
        briefing = run_daily_cycle(send_telegram=True)
        return {"status": "success", "briefing": briefing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return "<h1>Dashboard Mental Hedge em Construção...</h1>"
