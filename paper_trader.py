"""Motor de Paper Trading e Gerenciamento de Carteira Hipotética.
Utiliza banco SQLite local para registrar:
- Saldo total da carteira (Caixa Dólar SGOV + Caixa Real Selic + Alocações em Risco)
- Posições abertas em 3 mãos (1/3, 2/3, 3/3)
- Ordens com Stop Loss e Alvos Parciais
- Histórico de trades e rendimento diário de caixa
- Curva histórica de evolução patrimonial
"""
import sqlite3
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "paper_portfolio.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(initial_cash_usd=20000.0, initial_cash_brl=50000.0):
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Tabela de Carteira e Saldo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY,
                cash_usd REAL,
                cash_brl REAL,
                sgov_yield_daily REAL,
                selic_yield_daily REAL,
                updated_at TEXT
            )
        """)
        
        # Tabela de Posições Abertas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                direction TEXT NOT NULL, -- 'long' ou 'short'
                hand TEXT NOT NULL,      -- '1/3', '2/3', '3/3'
                quantity REAL NOT NULL,
                avg_entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                stop_loss REAL,
                target_1 REAL,
                target_2 REAL,
                breakeven_active INTEGER DEFAULT 0,
                allocated_usd REAL NOT NULL,
                opened_at TEXT NOT NULL,
                status TEXT DEFAULT 'OPEN', -- 'OPEN', 'CLOSED'
                strategy_notes TEXT
            )
        """)
        
        # Tabela de Histórico de Trades Fechados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                pnl_usd REAL NOT NULL,
                pnl_pct REAL NOT NULL,
                duration_days INTEGER,
                exit_reason TEXT, -- 'TARGET_1', 'TARGET_2', 'STOP_0A0', 'STOP_LOSS'
                closed_at TEXT NOT NULL,
                autopsy_notes TEXT
            )
        """)
        
        # Tabela de Histórico Diário de Patrimônio (Curva de Capital)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equity_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                cash_usd REAL NOT NULL,
                cash_brl REAL NOT NULL,
                allocated_usd REAL NOT NULL,
                total_usd REAL NOT NULL,
                daily_yield_usd REAL DEFAULT 0,
                daily_yield_brl REAL DEFAULT 0,
                notes TEXT
            )
        """)
        
        # Inicializa o saldo se ainda não existir
        cursor.execute("SELECT COUNT(*) FROM portfolio")
        if cursor.fetchone()[0] == 0:
            now = datetime.datetime.now().isoformat()
            sgov_daily = (1 + 0.048)**(1/252) - 1
            selic_daily = (1 + 0.1075)**(1/252) - 1
            cursor.execute("""
                INSERT INTO portfolio (id, cash_usd, cash_brl, sgov_yield_daily, selic_yield_daily, updated_at)
                VALUES (1, ?, ?, ?, ?, ?)
            """, (initial_cash_usd, initial_cash_brl, sgov_daily, selic_daily, now))
        conn.commit()
    print("[OK] Banco de Paper Trading (SQLite) inicializado com sucesso!")

def record_daily_snapshot(daily_yield_usd=0.0, daily_yield_brl=0.0, notes="Snapshot diário"):
    summary = get_portfolio_summary()
    today = datetime.date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO equity_history (date, cash_usd, cash_brl, allocated_usd, total_usd, daily_yield_usd, daily_yield_brl, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                cash_usd = excluded.cash_usd,
                cash_brl = excluded.cash_brl,
                allocated_usd = excluded.allocated_usd,
                total_usd = excluded.total_usd,
                daily_yield_usd = daily_yield_usd + excluded.daily_yield_usd,
                daily_yield_brl = daily_yield_brl + excluded.daily_yield_brl,
                notes = excluded.notes
        """, (
            today,
            summary["cash_usd"],
            summary["cash_brl"],
            summary["allocated_usd"],
            summary["total_portfolio_usd"],
            daily_yield_usd,
            daily_yield_brl,
            notes
        ))
        conn.commit()

def open_hand_position(asset: str, direction: str, hand: str, entry_price: float, 
                       stop_loss: float, target_1: float, target_2: float, 
                       allocation_usd: float, strategy_notes: str = ""):
    """Abre uma posição respeitando o modelo em 3 Mãos (1/3, 2/3, 3/3).
    Deduz o valor alocado do caixa USD em SGOV.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cash_usd FROM portfolio WHERE id = 1")
        row = cursor.fetchone()
        current_cash = row["cash_usd"] if row else 0.0
        
        if allocation_usd > current_cash:
            raise ValueError(f"Saldo insuficiente em caixa SGOV. Disponível: ${current_cash:.2f}, Solicitado: ${allocation_usd:.2f}")
            
        quantity = allocation_usd / entry_price if entry_price > 0 else 0
        now = datetime.datetime.now().isoformat()
        
        # Deduz do caixa
        cursor.execute("UPDATE portfolio SET cash_usd = cash_usd - ?, updated_at = ? WHERE id = 1", (allocation_usd, now))
        
        # Registra posição
        cursor.execute("""
            INSERT INTO positions (
                asset, direction, hand, quantity, avg_entry_price, current_price,
                stop_loss, target_1, target_2, breakeven_active, allocated_usd,
                opened_at, status, strategy_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 'OPEN', ?)
        """, (asset, direction.lower(), hand, quantity, entry_price, entry_price, stop_loss, target_1, target_2, allocation_usd, now, strategy_notes))
        
        pos_id = cursor.lastrowid
        conn.commit()
        return pos_id

def evaluate_breakeven_and_exits(current_prices: dict):
    """Varre as posições abertas aplicando as regras do Playbook:
    1. Regra dos +5%: se lucro >= 5%, realiza 1/3 (lucro no bolso) e move Stop para o 0 a 0.
    2. Stop Loss ou Breakeven atingido: encerra a posição e devolve capital ao caixa.
    3. Alvo 2 atingido: encerra totalmente no lucro máximo.
    """
    events = []
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions WHERE status = 'OPEN'")
        positions = [dict(r) for r in cursor.fetchall()]
        now = datetime.datetime.now().isoformat()
        
        for pos in positions:
            asset = pos["asset"]
            if asset not in current_prices:
                continue
            
            px = current_prices[asset]
            pos_id = pos["id"]
            direction = pos["direction"]
            entry = pos["avg_entry_price"]
            stop = pos["stop_loss"]
            t1 = pos["target_1"]
            t2 = pos["target_2"]
            be_active = pos["breakeven_active"]
            
            # Cálculo do PnL percentual
            pnl_pct = ((px - entry) / entry * 100) if direction == "long" else ((entry - px) / entry * 100)
            
            # Atualiza preço atual
            cursor.execute("UPDATE positions SET current_price = ? WHERE id = ?", (px, pos_id))
            
            # REGRA 1: Breakeven aos +5%
            if pnl_pct >= 5.0 and not be_active:
                cursor.execute("""
                    UPDATE positions 
                    SET stop_loss = avg_entry_price, breakeven_active = 1
                    WHERE id = ?
                """, (pos_id,))
                msg = f"🛡️ [BREAKEVEN ATIVADO] {asset} atingiu +{pnl_pct:.2f}%. Stop movido para 0 a 0 (US$ {entry:,.2f}). Risco zero!"
                events.append(msg)
                
            # REGRA 2: Stop Loss ou Stop no 0 a 0 atingido
            is_stopped = (direction == "long" and px <= stop) or (direction == "short" and px >= stop)
            if is_stopped:
                reason = "STOP_0A0" if be_active else "STOP_LOSS"
                pnl_usd = (pos["quantity"] * (px - entry)) if direction == "long" else (pos["quantity"] * (entry - px))
                returned_cash = pos["allocated_usd"] + pnl_usd
                
                cursor.execute("UPDATE positions SET status = 'CLOSED' WHERE id = ?", (pos_id,))
                cursor.execute("UPDATE portfolio SET cash_usd = cash_usd + ?, updated_at = ? WHERE id = 1", (returned_cash, now))
                cursor.execute("""
                    INSERT INTO trade_history (asset, direction, entry_price, exit_price, pnl_usd, pnl_pct, duration_days, exit_reason, closed_at, autopsy_notes)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """, (asset, direction, entry, px, pnl_usd, pnl_pct, reason, now, "Fechado por regra de stop."))
                
                msg = f"🛑 [STOP EXECUTADO] {asset} fechou a US$ {px:,.2f} ({reason}). PnL: ${pnl_usd:,.2f} ({pnl_pct:.2f}%)."
                events.append(msg)
                continue
                
            # REGRA 3: Alvo 2 (Saída total)
            is_target2 = (direction == "long" and px >= t2) if t2 else False
            if direction == "short" and t2:
                is_target2 = px <= t2
                
            if is_target2:
                pnl_usd = (pos["quantity"] * (px - entry)) if direction == "long" else (pos["quantity"] * (entry - px))
                returned_cash = pos["allocated_usd"] + pnl_usd
                cursor.execute("UPDATE positions SET status = 'CLOSED' WHERE id = ?", (pos_id,))
                cursor.execute("UPDATE portfolio SET cash_usd = cash_usd + ?, updated_at = ? WHERE id = 1", (returned_cash, now))
                cursor.execute("""
                    INSERT INTO trade_history (asset, direction, entry_price, exit_price, pnl_usd, pnl_pct, duration_days, exit_reason, closed_at, autopsy_notes)
                    VALUES (?, ?, ?, ?, ?, ?, 1, 'TARGET_2', ?, ?)
                """, (asset, direction, entry, px, pnl_usd, pnl_pct, now, "Alvo estrutural máximo alcançado."))
                
                msg = f"🎯 [ALVO 2 ATINGIDO] {asset} fechou com sucesso a US$ {px:,.2f}! Lucro: +${pnl_usd:,.2f} (+{pnl_pct:.2f}%)."
                events.append(msg)
                
        conn.commit()
    return events

def get_portfolio_summary():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio WHERE id = 1")
        row = cursor.fetchone()
        port = dict(row) if row else {"cash_usd": 20000.0, "cash_brl": 50000.0}
        
        cursor.execute("SELECT * FROM positions WHERE status = 'OPEN'")
        positions = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM trade_history ORDER BY closed_at DESC LIMIT 15")
        history = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM equity_history ORDER BY date ASC LIMIT 60")
        equity_curve = [dict(r) for r in cursor.fetchall()]
        
        allocated_usd = sum(p["allocated_usd"] for p in positions)
        total_usd = port["cash_usd"] + allocated_usd
        
        return {
            "cash_usd": round(port["cash_usd"], 2),
            "cash_brl": round(port["cash_brl"], 2),
            "allocated_usd": round(allocated_usd, 2),
            "total_portfolio_usd": round(total_usd, 2),
            "active_positions_count": len(positions),
            "positions": positions,
            "recent_history": history,
            "equity_curve": equity_curve
        }

if __name__ == "__main__":
    init_db()
    record_daily_snapshot()
    print(get_portfolio_summary())
