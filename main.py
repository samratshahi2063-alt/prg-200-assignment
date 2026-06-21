import streamlit as st
from datetime import date
from database import init_db, add_subject, get_subjects, log_session, get_sessions, set_goal, get_goal
from tracker import get_summary, get_ml_suggestion
from charts import get_daily_chart, get_subject_chart
import pandas as pd
import sqlite3

init_db()

DB = "study_tracker.db"

def delete_session(rowid):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE rowid=?", (rowid,))
    conn.commit()
    conn.close()

def delete_subject(subject_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
    cur.execute("DELETE FROM sessions WHERE subject_id=?", (subject_id,))
    conn.commit()
    conn.close()

def get_sessions_with_id():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT s.rowid, s.date, sub.name, s.duration, s.notes
        FROM sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        ORDER BY s.date DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_weekly_summary():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT sub.name, SUM(s.duration)
        FROM sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        WHERE s.date >= date('now', '-7 days')
        GROUP BY sub.name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_monthly_summary():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT sub.name, SUM(s.duration)
        FROM sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        WHERE s.date >= date('now', '-30 days')
        GROUP BY sub.name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

st.markdown("""
    <style>
        .main { background-color: #f5f7fa; }
        .block-container { padding-top: 2rem; }
        h1 { color: #1a1a2e; }
        h2, h3 { color: #16213e; }
        .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
        .stButton>button { background-color: #0f3460; color: white; border-radius: 8px; padding: 8px 20px; border: none; }
        .stButton>button:hover { background-color: #e94560; color: white; }
        .stSelectbox, .stTextInput, .stNumberInput { background-color: #ffffff; }
        .sidebar .sidebar-content { background-color: #1a1a2e; }
    </style>
""", unsafe_allow_html=True)

st.title("Student Study Tracker System")

menu = st.sidebar.selectbox("Menu", [
    "Dashboard",
    "Log Session",
    "Manage Subjects",
    "Set Goal",
    "History",
    "Charts",
    "ML Suggestion",
    "Weekly Report",
    "Monthly Report"
])

if menu == "Dashboard":
    st.header("Dashboard")
    today_mins, goal, streak = get_summary()

    col1, col2, col3 = st.columns(3)
    col1.metric("Today's Study Time", f"{today_mins} mins")
    col2.metric("Daily Goal", f"{goal} mins")
    col3.metric("Streak", f"{streak} day(s)")

    st.subheader("Today's Goal Progress")
    if goal > 0:
        percent = min(today_mins / goal, 1.0)
        st.progress(percent)
        percent_display = round(percent * 100)
        if percent_display >= 100:
            st.success(f"Goal completed! You studied {today_mins} mins out of {goal} mins.")
        else:
            st.info(f"{percent_display}% of daily goal completed. {goal - today_mins} mins left.")
    else:
        st.warning("No daily goal set. Go to Set Goal to set one.")

elif menu == "Log Session":
    st.header("Log Study Session")
    subjects = get_subjects()

    if not subjects:
        st.warning("No subjects found. Please add subjects first.")
    else:
        subject_map = {name: sid for sid, name in subjects}
        subject_name = st.selectbox("Select Subject", list(subject_map.keys()))
        duration = st.number_input("Duration (minutes)", min_value=1, step=1)
        notes = st.text_input("Notes (optional)")

        if st.button("Save Session"):
            sid = subject_map[subject_name]
            log_session(sid, str(date.today()), duration, notes)
            st.success("Session logged!")

elif menu == "Manage Subjects":
    st.header("Manage Subjects")

    new_subject = st.text_input("Enter subject name")
    if st.button("Add Subject"):
        if new_subject.strip():
            add_subject(new_subject.strip())
            st.success(f"Subject '{new_subject}' added!")
        else:
            st.error("Please enter a subject name.")

    st.subheader("Your Subjects")
    subjects = get_subjects()
    if subjects:
        for sid, name in subjects:
            col1, col2 = st.columns([4, 1])
            col1.write(f"- {name}")
            if col2.button("Delete", key=f"del_sub_{sid}"):
                delete_subject(sid)
                st.warning(f"Subject '{name}' and all its sessions deleted.")
                st.rerun()
    else:
        st.info("No subjects added yet.")

elif menu == "Set Goal":
    st.header("Set Daily Goal")
    current = get_goal()
    st.info(f"Current goal: {current} mins/day")
    goal_input = st.number_input("New daily goal (minutes)", min_value=1, step=1)

    if st.button("Save Goal"):
        set_goal(int(goal_input))
        st.success(f"Goal set to {goal_input} minutes per day!")

elif menu == "History":
    st.header("Study History")
    sessions = get_sessions_with_id()

    if not sessions:
        st.info("No sessions logged yet.")
    else:
        subjects = get_subjects()
        subject_names = ["All"] + [name for _, name in subjects]

        col1, col2 = st.columns(2)
        filter_subject = col1.selectbox("Filter by Subject", subject_names)
        filter_date = col2.date_input("Filter by Date (optional)", value=None)

        filtered = sessions
        if filter_subject != "All":
            filtered = [s for s in filtered if s[2] == filter_subject]
        if filter_date:
            filtered = [s for s in filtered if s[1] == str(filter_date)]

        if not filtered:
            st.warning("No sessions match your filter.")
        else:
            for row in filtered:
                rowid, d, subject, duration, notes = row
                col1, col2 = st.columns([5, 1])
                col1.write(f"**{d}** | {subject} | {duration} mins | {notes}")
                if col2.button("Delete", key=f"del_ses_{rowid}"):
                    delete_session(rowid)
                    st.warning("Session deleted.")
                    st.rerun()

elif menu == "Charts":
    st.header("Study Charts")
    _, goal, _ = get_summary()

    daily_chart = get_daily_chart(goal)
    if daily_chart:
        st.subheader("Daily Study Time")
        st.pyplot(daily_chart)
    else:
        st.info("No data yet for daily chart.")

    subject_chart = get_subject_chart()
    if subject_chart:
        st.subheader("Time Per Subject")
        st.pyplot(subject_chart)
    else:
        st.info("No data yet for subject chart.")

elif menu == "ML Suggestion":
    st.header("ML Study Suggestion")
    st.info("This feature looks at your study history and tells you which subject needs more attention.")
    suggestion = get_ml_suggestion()
    st.write(suggestion)

elif menu == "Weekly Report":
    st.header("Weekly Report (Last 7 Days)")
    data = get_weekly_summary()

    if not data:
        st.info("No study sessions in the last 7 days.")
    else:
        df = pd.DataFrame(data, columns=["Subject", "Total Minutes"])
        df = df.sort_values("Total Minutes", ascending=False)
        total = df["Total Minutes"].sum()
        st.metric("Total Study Time This Week", f"{total} mins")
        st.dataframe(df, use_container_width=True)

elif menu == "Monthly Report":
    st.header("Monthly Report (Last 30 Days)")
    data = get_monthly_summary()

    if not data:
        st.info("No study sessions in the last 30 days.")
    else:
        df = pd.DataFrame(data, columns=["Subject", "Total Minutes"])
        df = df.sort_values("Total Minutes", ascending=False)
        total = df["Total Minutes"].sum()
        st.metric("Total Study Time This Month", f"{total} mins")
        st.dataframe(df, use_container_width=True)