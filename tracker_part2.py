from database import get_connection
from datetime import date, timedelta

def set_goal(user_id, daily_goal_minutes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM goals WHERE user_id=?", (user_id,))
    exists = cursor.fetchone()
    if exists:
        cursor.execute("UPDATE goals SET daily_goal_minutes=? WHERE user_id=?", (daily_goal_minutes, user_id))
    else:
        cursor.execute("INSERT INTO goals (user_id, daily_goal_minutes) VALUES (?, ?)", (user_id, daily_goal_minutes))
    conn.commit()
    conn.close()

def get_goal(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT daily_goal_minutes FROM goals WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def get_streak(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT date FROM sessions
        WHERE user_id=?
        ORDER BY date DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return 0

    streak = 0
    check_date = date.today()

    for (d,) in rows:
        session_date = date.fromisoformat(d)
        if session_date == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return streak

def get_today_summary(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    today = str(date.today())
    cursor.execute("""
        SELECT SUM(duration_minutes) FROM sessions
        WHERE user_id=? AND date=?
    """, (user_id, today))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row[0] else 0