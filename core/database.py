"""
database.py — SQLite ORM helpers for FaceRecAtd (Simplified)
Tables: users, attendance
"""

import sqlite3
import os
import json
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "attendance.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            employee_id     TEXT    UNIQUE NOT NULL,
            department      TEXT,
            role            TEXT    DEFAULT 'employee',
            face_encoding   BLOB,
            photo_path      TEXT,
            registered_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active       INTEGER DEFAULT 1,
            is_in_food_program INTEGER DEFAULT 1
        )
    """)
    # Ensure existing users get the new column if upgrading from older DB
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_in_food_program INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass # Column might already exist
        
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            employee_id TEXT    NOT NULL,
            date        DATE    NOT NULL,
            check_in    DATETIME,
            check_out   DATETIME,
            status      TEXT    DEFAULT 'Present',
            method      TEXT    DEFAULT 'face',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_user_date
        ON attendance(user_id, date)
    """)
    
    # New Meal Logs Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS meal_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            employee_id TEXT    NOT NULL,
            date        DATE    NOT NULL,
            meal_type   TEXT    NOT NULL,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_meal_logs_user_date_meal
        ON meal_logs(user_id, date, meal_type)
    """)
    conn.commit()
    conn.close()


def _serialize_face_encoding(face_encoding):
    if face_encoding is None:
        return None
    return json.dumps([float(v) for v in face_encoding])


def _deserialize_face_encoding(raw_value):
    if raw_value is None:
        return None
    if isinstance(raw_value, bytes):
        try:
            raw_value = raw_value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    try:
        parsed = json.loads(raw_value)
    except Exception:
        return None
    if not isinstance(parsed, list):
        return None
    try:
        return [float(v) for v in parsed]
    except Exception:
        return None


# ─── USERS ────────────────────────────────────────────────────────────────────

def add_user(name, employee_id, department, role, face_encoding=None, photo_path=None, is_in_food_program=1):
    conn = _get_conn()
    c = conn.cursor()
    enc_blob = _serialize_face_encoding(face_encoding)
    try:
        c.execute("""
            INSERT INTO users (name, employee_id, department, role, face_encoding, photo_path, is_in_food_program)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, employee_id, department, role, enc_blob, photo_path, is_in_food_program))
        conn.commit()
        return True, "User registered successfully"
    except sqlite3.IntegrityError:
        return False, "Employee ID already exists"
    finally:
        conn.close()


def get_all_users():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, name, employee_id, department, role, photo_path, registered_at, is_active, is_in_food_program
        FROM users ORDER BY registered_at DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_user_by_id(employee_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE employee_id = ? AND is_active = 1", (employee_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_face_encodings():
    """Return list of dicts: {user_id, employee_id, name, encoding}."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, employee_id, name, face_encoding
        FROM users WHERE face_encoding IS NOT NULL AND is_active = 1
    """)
    result = []
    for row in c.fetchall():
        encoding = _deserialize_face_encoding(row["face_encoding"])
        if encoding is None:
            continue
        result.append({
            "user_id": row["id"],
            "employee_id": row["employee_id"],
            "name": row["name"],
            "encoding": encoding,
        })
    conn.close()
    return result


def deactivate_user(employee_id):
    import os
    conn = _get_conn()
    c = conn.cursor()
    
    # 1. Fetch and delete the physical image file
    c.execute("SELECT photo_path FROM users WHERE employee_id = ?", (employee_id,))
    row = c.fetchone()
    if row and row["photo_path"]:
        photo_path = row["photo_path"]
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except Exception as e:
                print(f"Failed to delete image {photo_path}: {e}")

    # 2. Hard delete the user from the database
    c.execute("DELETE FROM users WHERE employee_id = ?", (employee_id,))
    
    # 3. Clean up associated meal logs so they don't become orphaned
    c.execute("DELETE FROM meal_logs WHERE employee_id = ?", (employee_id,))
    
    # 4. Clean up any data from the legacy attendance table
    c.execute("DELETE FROM attendance WHERE employee_id = ?", (employee_id,))
    
    conn.commit()
    conn.close()


def toggle_food_program(employee_id, status):
    """Update a user's food program enrollment status (1 or 0)"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET is_in_food_program = ? WHERE employee_id = ?", (status, employee_id))
    conn.commit()
    conn.close()


def get_departments():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT department FROM users WHERE department IS NOT NULL AND is_active = 1")
    depts = [r[0] for r in c.fetchall()]
    conn.close()
    return depts


# ─── ATTENDANCE (Legacy/General) ──────────────────────────────────────────────
# (Kept for backwards compatibility if needed)

def mark_attendance(user_id, employee_id, method="face"):
    """
    Returns: (action, timestamp)
    action: "check_in" | "check_out" | "already_complete"
    """
    conn = _get_conn()
    c = conn.cursor()
    today = date.today()
    now = datetime.now()
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute("""
            INSERT OR IGNORE INTO attendance (user_id, employee_id, date, check_in, status, method)
            VALUES (?, ?, ?, ?, 'Present', ?)
        """, (user_id, employee_id, today, now, method))

        if c.rowcount == 1:
            conn.commit()
            return "check_in", now

        c.execute("""
            UPDATE attendance
            SET check_out = ?
            WHERE user_id = ? AND date = ? AND check_out IS NULL
        """, (now, user_id, today))

        if c.rowcount == 1:
            conn.commit()
            return "check_out", now

        conn.commit()
        return "already_complete", now
    finally:
        conn.close()

def get_attendance_records(date_from=None, date_to=None, department=None, employee_id=None):
    conn = _get_conn()
    c = conn.cursor()
    query = """
        SELECT a.id, a.employee_id, a.date, a.check_in, a.check_out, a.status, a.method,
               u.name, u.department, u.role
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE u.is_active = 1
    """
    params = []
    if date_from:
        query += " AND a.date >= ?"
        params.append(str(date_from))
    if date_to:
        query += " AND a.date <= ?"
        params.append(str(date_to))
    if department:
        query += " AND u.department = ?"
        params.append(department)
    if employee_id:
        query += " AND a.employee_id = ?"
        params.append(employee_id)
    query += " ORDER BY a.date DESC, a.check_in DESC"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_daily_counts(days=14):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT a.date, COUNT(*) as count
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE a.date >= date('now', ?) AND u.is_active = 1
        GROUP BY a.date
        ORDER BY a.date ASC
    """, (f"-{days} days",))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ─── MEAL LOGS (Food Mess) ───────────────────────────────────────────────────

def log_meal(user_id, employee_id, meal_type):
    """
    Returns: (status, timestamp)
    status: "success" | "not_enrolled" | "already_logged"
    """
    conn = _get_conn()
    c = conn.cursor()
    today = date.today()
    now = datetime.now()
    try:
        c.execute("BEGIN IMMEDIATE")
        
        # 1. Check if user is enrolled in food program
        c.execute("SELECT is_in_food_program FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        if not row or not row["is_in_food_program"]:
            return "not_enrolled", now
            
        # 2. Attempt to log the meal
        c.execute("""
            INSERT OR IGNORE INTO meal_logs (user_id, employee_id, date, meal_type, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, employee_id, today, meal_type, now))

        if c.rowcount == 1:
            conn.commit()
            return "success", now

        conn.commit()
        return "already_logged", now
    finally:
        conn.close()


def get_meal_logs(date_from=None, date_to=None, department=None, employee_id=None):
    conn = _get_conn()
    c = conn.cursor()
    query = """
        SELECT m.id, m.employee_id, m.date, m.meal_type, m.timestamp,
               u.name, u.department, u.role
        FROM meal_logs m
        JOIN users u ON m.user_id = u.id
        WHERE u.is_active = 1
    """
    params = []
    if date_from:
        query += " AND m.date >= ?"
        params.append(str(date_from))
    if date_to:
        query += " AND m.date <= ?"
        params.append(str(date_to))
    if department:
        query += " AND u.department = ?"
        params.append(department)
    if employee_id:
        query += " AND m.employee_id = ?"
        params.append(employee_id)
    query += " ORDER BY m.date DESC, m.timestamp DESC"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def clear_meal_logs():
    """Delete all records from the meal_logs table."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM meal_logs")
    conn.commit()
    conn.close()


def get_today_meal_summary():
    conn = _get_conn()
    c = conn.cursor()
    today = date.today()
    
    c.execute("""
        SELECT meal_type, COUNT(*) as count 
        FROM meal_logs m 
        JOIN users u ON m.user_id = u.id 
        WHERE m.date = ? AND u.is_active = 1
        GROUP BY meal_type
    """, (today,))
    
    summary = {"Breakfast": 0, "Lunch": 0, "Dinner": 0}
    for row in c.fetchall():
        if row["meal_type"] in summary:
            summary[row["meal_type"]] = row["count"]
            
    c.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND is_in_food_program = 1")
    total_enrolled = c.fetchone()[0]
    
    conn.close()
    return {"meals": summary, "total_enrolled": total_enrolled}


def get_daily_meal_counts(days=14):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT date, COUNT(*) as count
        FROM meal_logs m
        JOIN users u ON m.user_id = u.id
        WHERE m.date >= date('now', ?) AND u.is_active = 1
        GROUP BY m.date
        ORDER BY m.date ASC
    """, (f"-{days} days",))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

