import sqlite3
from datetime import datetime
DB_NAME = "study_planner.db"
def get_conn():
    return sqlite3.connect(DB_NAME)
def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    description TEXT,
                    deadline TEXT,
                    completed INTEGER DEFAULT 0,
                    category TEXT DEFAULT 'General',
                    priority TEXT DEFAULT 'Medium',
                    created_at TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )''')

    conn.commit()
    conn.close()
def add_task(subject, description, deadline, category='General', priority='Medium'):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (subject, description, deadline, category, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (subject, description, deadline, category, priority, datetime.now().isoformat()))
    conn.commit()
    conn.close()
def get_tasks():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks ORDER BY completed ASC, priority DESC, deadline IS NOT NULL, deadline")
    rows = c.fetchall()
    conn.close()
    return rows
def get_task(task_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
    row = c.fetchone()
    conn.close()
    return row
def delete_task(task_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
def update_task(task_id, subject=None, description=None, deadline=None, category=None, priority=None, completed=None):
    conn = get_conn()
    c = conn.cursor()
    updates = []
    params = []
    if subject is not None:
        updates.append("subject=?"); params.append(subject)
    if description is not None:
        updates.append("description=?"); params.append(description)
    if deadline is not None:
        updates.append("deadline=?"); params.append(deadline)
    if category is not None:
        updates.append("category=?"); params.append(category)
    if priority is not None:
        updates.append("priority=?"); params.append(priority)
    if completed is not None:
        updates.append("completed=?"); params.append(1 if completed else 0)
    if not updates:
        conn.close()
        return
    params.append(task_id)
    sql = "UPDATE tasks SET " + ", ".join(updates) + " WHERE id=?"
    c.execute(sql, tuple(params))
    conn.commit()
    conn.close()
def mark_task_complete(task_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE tasks SET completed=1 WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
def mark_task_incomplete(task_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE tasks SET completed=0 WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
def save_chat(sender, message):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (sender, message, timestamp) VALUES (?, ?, ?)",
              (sender, message, datetime.now().isoformat()))
    conn.commit()
    conn.close()
def get_chat_history(limit=20):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT sender, message FROM chat_history ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows[::-1] 
def get_stats():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tasks")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tasks WHERE completed=1")
    completed = c.fetchone()[0]
    c.execute("SELECT priority, COUNT(*) FROM tasks GROUP BY priority")
    by_priority = dict(c.fetchall())
    c.execute("SELECT category, COUNT(*) FROM tasks GROUP BY category")
    by_category = dict(c.fetchall())
    conn.close()
    pct = int((completed / total) * 100) if total > 0 else 0
    return {"total": total, "completed": completed, "percent_complete": pct, "by_priority": by_priority, "by_category": by_category}


