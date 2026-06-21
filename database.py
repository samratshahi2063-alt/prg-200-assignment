import sqlite3
from datetime import date, timedelta

DB = "study_tracker.db"

COLOR_PALETTE = [
    "#6C63FF", "#FF6B6B", "#4ECDC4", "#FFD93D", "#1A8FE3",
    "#FF8C42", "#9B59B6", "#2ECC71", "#E74C3C", "#3498DB"
]


def get_connection():
    return sqlite3.connect(DB)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            date TEXT,
            duration INTEGER,
            notes TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY,
            daily_goal INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS best_streak (
            id INTEGER PRIMARY KEY,
            value INTEGER
        )
    """)

    conn.commit()
    conn.close()

def add_subject(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subjects")
    count = cur.fetchone()[0]
    color = COLOR_PALETTE[count % len(COLOR_PALETTE)]
    try:
        cur.execute("INSERT INTO subjects (name, color) VALUES (?, ?)", (name, color))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    return ok


def get_subjects():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, color FROM subjects ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_subject_color_map():
    return {name: color for _, name, color in get_subjects()}


def delete_subject(subject_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE subject_id=?", (subject_id,))
    cur.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
    conn.commit()
    conn.close()


def rename_subject(subject_id, new_name):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE subjects SET name=? WHERE id=?", (new_name, subject_id))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    return ok


def log_session(subject_id, session_date, duration, notes=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sessions (subject_id, date, duration, notes) VALUES (?, ?, ?, ?)",
        (subject_id, session_date, duration, notes)
    )
    conn.commit()
    conn.close()
    update_best_streak()


def get_sessions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.date, sub.name, s.duration, s.notes, sub.color
        FROM sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        ORDER BY s.date DESC, s.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_session(session_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    conn.commit()
    conn.close()


def update_session(session_id, duration, notes):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE sessions SET duration=?, notes=? WHERE id=?", (duration, notes, session_id))
    conn.commit()
    conn.close()


def get_subject_totals():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sub.name, SUM(s.duration), sub.color
        FROM sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        GROUP BY sub.name
        ORDER BY SUM(s.duration) DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_range_totals(days):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT sub.name, SUM(s.duration)
        FROM sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        WHERE s.date >= date('now', '-{days} days')
        GROUP BY sub.name
        ORDER BY SUM(s.duration) DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def set_goal(minutes):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM goals")
    cur.execute("INSERT INTO goals (id, daily_goal) VALUES (1, ?)", (minutes,))
    conn.commit()
    conn.close()


def get_goal():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT daily_goal FROM goals")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def get_today_total(today):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT SUM(duration) FROM sessions WHERE date=?", (today,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row[0] else 0


def get_day_total(day_str):
    return get_today_total(day_str)



def get_all_study_dates():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT date FROM sessions ORDER BY date DESC")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_streak():
    rows = get_all_study_dates()
    if not rows:
        return 0

    streak = 0
    check_date = date.today()

    for d in rows:
        session_date = date.fromisoformat(d)
        if session_date == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        elif session_date < check_date:
            break

    return streak


def update_best_streak():
    current = get_streak()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM best_streak WHERE id=1")
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO best_streak (id, value) VALUES (1, ?)", (current,))
    elif current > row[0]:
        cur.execute("UPDATE best_streak SET value=? WHERE id=1", (current,))
    conn.commit()
    conn.close()


def get_best_streak():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM best_streak WHERE id=1")
    row = cur.fetchone()
    conn.close()
    current = get_streak()
    best = row[0] if row else 0
    return max(best, current)


def get_goal_hit_days(days=7):
    """How many of the last N days met the daily goal."""
    goal = get_goal()
    if goal <= 0:
        return 0, days

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT date, SUM(duration) FROM sessions
        WHERE date >= date('now', '-{days} days')
        GROUP BY date
    """)
    rows = cur.fetchall()
    conn.close()

    hit_days = sum(1 for _, total in rows if total >= goal)
    return hit_days, days


def get_daily_series(days=30):
    """Minutes studied per day for the last N days, including zero days."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT date, SUM(duration) FROM sessions
        WHERE date >= date('now', '-{days} days')
        GROUP BY date
    """)
    rows = dict(cur.fetchall())
    conn.close()

    result = []
    for i in range(days, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        result.append((d, rows.get(d, 0)))
    return result


def get_subject_detail_stats():
    """
    For every subject, returns:
      name, total_minutes, session_count, distinct_days_studied,
      last_studied_date, avg_minutes_per_session
    This is the raw signal set the ML suggestion engine reasons over.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            sub.name,
            COALESCE(SUM(s.duration), 0) AS total_minutes,
            COUNT(s.id) AS session_count,
            COUNT(DISTINCT s.date) AS distinct_days,
            MAX(s.date) AS last_date,
            sub.color
        FROM subjects sub
        LEFT JOIN sessions s ON s.subject_id = sub.id
        GROUP BY sub.id
        ORDER BY total_minutes DESC
    """)
    rows = cur.fetchall()
    conn.close()

    today = date.today()
    stats = []
    for name, total, count, days_studied, last_date, color in rows:
        if last_date:
            days_since = (today - date.fromisoformat(last_date)).days
        else:
            days_since = None
        avg_session = round(total / count, 1) if count else 0
        stats.append({
            "name": name,
            "total_minutes": total,
            "session_count": count,
            "distinct_days": days_studied,
            "days_since_last": days_since,
            "avg_session_minutes": avg_session,
            "color": color,
        })
    return stats