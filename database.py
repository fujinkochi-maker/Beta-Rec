import sqlite3
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), "boxing.db")

DIVISIONS = [
    "Heavyweight","Cruiserweight","Light Heavyweight","Super Middleweight",
    "Middleweight","Super Welterweight","Welterweight","Super Lightweight",
    "Lightweight","Super Featherweight","Featherweight","Super Bantamweight",
    "Bantamweight","Super Flyweight","Flyweight","Minimumweight"
]
BELTS = ["WBC","WBO","IBF","WBA"]

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fighters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fighter_name TEXT NOT NULL,
                nickname TEXT DEFAULT '',
                discord_id TEXT UNIQUE,
                country TEXT DEFAULT '',
                division TEXT DEFAULT 'Heavyweight',
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                kos INTEGER DEFAULT 0,
                last_fight TEXT,
                is_verified INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winner TEXT NOT NULL,
                loser TEXT NOT NULL,
                method TEXT NOT NULL,
                round INTEGER,
                is_ko INTEGER DEFAULT 0,
                division TEXT DEFAULT 'Heavyweight',
                date TEXT DEFAULT (date('now')),
                logged_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS fight_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT DEFAULT '',
            fighter1 TEXT NOT NULL,
            fighter2 TEXT NOT NULL,
            division TEXT DEFAULT 'Heavyweight',
            fight_date TEXT,
            event_name TEXT DEFAULT '',
            status TEXT DEFAULT 'upcoming',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            detail TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS championships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                belt TEXT NOT NULL,
                division TEXT NOT NULL,
                champion TEXT,
                won_date TEXT,
                defenses INTEGER DEFAULT 0,
                UNIQUE(belt, division)
            );
        """)
        # Migrate old roblox_username column if needed
        try:
            conn.execute("ALTER TABLE fighters ADD COLUMN fighter_name TEXT")
        except: pass
        try:
            conn.execute("ALTER TABLE fighters ADD COLUMN nickname TEXT DEFAULT ''")
        except: pass
        try:
            conn.execute("ALTER TABLE fighters ADD COLUMN country TEXT DEFAULT ''")
        except: pass
        try:
            conn.execute("ALTER TABLE fighters ADD COLUMN is_verified INTEGER DEFAULT 0")
        except: pass

def dict_row(row):
    return dict(row) if row else None

# ── Fighter CRUD ──────────────────────────────────────────

def register_fighter(fighter_name, discord_id=None, division="Heavyweight", nickname="", country=""):
    """Register a fighter by discord ID — no roblox needed."""
    with get_conn() as conn:
        # Check if fighter_name already exists without a discord_id — update it
        existing_name = conn.execute(
            "SELECT * FROM fighters WHERE fighter_name=? COLLATE NOCASE", (fighter_name,)
        ).fetchone()
        if existing_name and not existing_name["discord_id"] and discord_id:
            conn.execute("""
                UPDATE fighters SET discord_id=?, division=?, nickname=?, country=?, is_verified=1
                WHERE fighter_name=? COLLATE NOCASE
            """, (discord_id, division, nickname, country, fighter_name))
            return
        # Check if discord_id already registered — update their info
        if discord_id:
            existing_discord = conn.execute(
                "SELECT * FROM fighters WHERE discord_id=?", (discord_id,)
            ).fetchone()
            if existing_discord:
                conn.execute("""
                    UPDATE fighters SET fighter_name=?, division=?, nickname=?, country=?, is_verified=1
                    WHERE discord_id=?
                """, (fighter_name, division, nickname, country, discord_id))
                return
        # Fresh insert
        conn.execute("""
            INSERT OR IGNORE INTO fighters (fighter_name, discord_id, division, nickname, country, is_verified)
            VALUES (?,?,?,?,?,1)
        """, (fighter_name, discord_id, division, nickname, country))

def get_fighter_by_id(fighter_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fighters WHERE id=?", (fighter_id,)).fetchone()
        return dict_row(row)

def get_fighter_by_discord(discord_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fighters WHERE discord_id=?", (discord_id,)).fetchone()
        return dict_row(row)

def get_fighter_by_name(name):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fighters WHERE fighter_name=? COLLATE NOCASE", (name,)).fetchone()
        return dict_row(row)

def search_fighters(query):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM fighters WHERE fighter_name LIKE ? OR nickname LIKE ? ORDER BY wins DESC LIMIT 20",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
        return [dict(r) for r in rows]

def update_fighter_info(discord_id, fighter_name=None, nickname=None, country=None, division=None):
    with get_conn() as conn:
        f = dict_row(conn.execute("SELECT * FROM fighters WHERE discord_id=?", (discord_id,)).fetchone())
        if not f: return
        conn.execute("""
            UPDATE fighters SET
                fighter_name=?, nickname=?, country=?, division=?
            WHERE discord_id=?
        """, (
            fighter_name or f["fighter_name"],
            nickname if nickname is not None else f.get("nickname",""),
            country if country is not None else f.get("country",""),
            division or f["division"],
            discord_id
        ))

def manual_update_record(discord_id_or_name, wins, losses, draws, kos, division=None):
    with get_conn() as conn:
        f = dict_row(conn.execute("SELECT * FROM fighters WHERE discord_id=? OR fighter_name=? COLLATE NOCASE",
            (discord_id_or_name, discord_id_or_name)).fetchone())
        if not f: return None
        conn.execute("""
            UPDATE fighters SET wins=?,losses=?,draws=?,kos=?,division=COALESCE(?,division)
            WHERE id=?
        """, (wins, losses, draws, kos, division, f["id"]))
        return dict_row(conn.execute("SELECT * FROM fighters WHERE id=?", (f["id"],)).fetchone())

def reset_record(discord_id_or_name):
    with get_conn() as conn:
        conn.execute("""
            UPDATE fighters SET wins=0,losses=0,draws=0,kos=0,last_fight=NULL
            WHERE discord_id=? OR fighter_name=? COLLATE NOCASE
        """, (discord_id_or_name, discord_id_or_name))

def delete_fighter(discord_id_or_name):
    with get_conn() as conn:
        conn.execute("DELETE FROM fighters WHERE discord_id=? OR fighter_name=? COLLATE NOCASE",
            (discord_id_or_name, discord_id_or_name))

def unverify_fighter(discord_id):
    with get_conn() as conn:
        conn.execute("UPDATE fighters SET is_verified=0 WHERE discord_id=?", (discord_id,))

def get_leaderboard(limit=20, division=None):
    with get_conn() as conn:
        if division:
            rows = conn.execute("SELECT * FROM fighters WHERE (wins+losses)>0 AND division=? ORDER BY wins DESC,kos DESC LIMIT ?",
                (division, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM fighters WHERE (wins+losses)>0 ORDER BY wins DESC,kos DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_rankings(division=None, limit=20):
    with get_conn() as conn:
        if division:
            rows = conn.execute("""
                SELECT *,CAST(wins AS REAL)/(wins+losses) AS win_rate
                FROM fighters WHERE (wins+losses)>0 AND division=?
                ORDER BY win_rate DESC,wins DESC LIMIT ?""", (division, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT *,CAST(wins AS REAL)/(wins+losses) AS win_rate
                FROM fighters WHERE (wins+losses)>0
                ORDER BY win_rate DESC,wins DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_fighter_rank(discord_id_or_name, division=None):
    with get_conn() as conn:
        if division:
            rows = conn.execute("SELECT discord_id,fighter_name FROM fighters WHERE (wins+losses)>0 AND division=? ORDER BY wins DESC,kos DESC", (division,)).fetchall()
        else:
            rows = conn.execute("SELECT discord_id,fighter_name FROM fighters WHERE (wins+losses)>0 ORDER BY wins DESC,kos DESC").fetchall()
        for i, r in enumerate(rows):
            if r["discord_id"] == discord_id_or_name or (r["fighter_name"] or "").lower() == discord_id_or_name.lower():
                return i+1
        return None

def get_all_fighters():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM fighters ORDER BY wins DESC").fetchall()
        return [dict(r) for r in rows]

# ── Matches ───────────────────────────────────────────────

def add_match(winner_name, loser_name, method, round_num, is_ko, division="Heavyweight"):
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute("INSERT INTO matches (winner,loser,method,round,is_ko,division,date) VALUES (?,?,?,?,?,?,?)",
            (winner_name, loser_name, method, round_num, 1 if is_ko else 0, division, today))
        conn.execute("UPDATE fighters SET wins=wins+1,kos=kos+?,last_fight=? WHERE fighter_name=? COLLATE NOCASE",
            (1 if is_ko else 0, today, winner_name))
        conn.execute("UPDATE fighters SET losses=losses+1,last_fight=? WHERE fighter_name=? COLLATE NOCASE",
            (today, loser_name))

def get_match_history(filter_name=None, limit=30, division=None):
    with get_conn() as conn:
        if filter_name:
            rows = conn.execute("SELECT * FROM matches WHERE winner=? COLLATE NOCASE OR loser=? COLLATE NOCASE ORDER BY logged_at DESC LIMIT ?",
                (filter_name, filter_name, limit)).fetchall()
        elif division:
            rows = conn.execute("SELECT * FROM matches WHERE division=? ORDER BY logged_at DESC LIMIT ?", (division, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM matches ORDER BY logged_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_all_matches(limit=100):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM matches ORDER BY logged_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def delete_match(match_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM matches WHERE id=?", (match_id,))

# ── Championships ─────────────────────────────────────────


def log_activity(username, action, detail=""):
    with get_conn() as conn:
        conn.execute("INSERT INTO activity_log (username, action, detail) VALUES (?,?,?)",
            (username, action, detail))

def get_all_championships():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM championships ORDER BY division,belt").fetchall()
        return [dict(r) for r in rows]

def get_fighter_belts(fighter_name):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM championships WHERE champion=? COLLATE NOCASE", (fighter_name,)).fetchall()
        return [dict(r) for r in rows]

def set_champion(belt, division, champion):
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO championships (belt,division,champion,won_date,defenses) VALUES (?,?,?,?,0)",
            (belt, division, champion, today))

def remove_champion(belt, division):
    with get_conn() as conn:
        conn.execute("UPDATE championships SET champion=NULL,won_date=NULL,defenses=0 WHERE belt=? AND division=?", (belt, division))

def add_defense(belt, division):
    with get_conn() as conn:
        conn.execute("UPDATE championships SET defenses=defenses+1 WHERE belt=? AND division=?", (belt, division))
