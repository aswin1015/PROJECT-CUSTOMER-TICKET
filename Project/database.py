import sqlite3
from datetime import datetime
from typing import Optional, List
from threading import Lock

DATABASE_NAME = "tickets.db"

db_lock = Lock()


# -------------------- MODELS --------------------

class Ticket:
    def __init__(
        self,
        ticket_id,
        title,
        description,
        priority,
        status,
        assigned_to,
        created_by,
        created_at,
        updated_at,
    ):
        self.id = ticket_id
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status
        self.assigned_to = assigned_to
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
        "id": self.id,
        "title": self.title,
        "description": self.description,
        "priority": self.priority,
        "status": self.status,
        "assigned_to": self.assigned_to,
        "created_by": getattr(self, "created_by", None),
        "created_at": getattr(self, "created_at", None),
        "updated_at": getattr(self, "updated_at", None),
        "resolved_at": getattr(self, "resolved_at", None),
        "closed_at": getattr(self, "closed_at", None),
    }

    

    def __repr__(self):
        return f"Ticket(id={self.id}, title={self.title}, status={self.status})"



class Comment:
    def __init__(self, author, comment, is_internal):
        self.author = author
        self.comment = comment
        self.is_internal = is_internal


# -------------------- CONNECTION --------------------

def get_connection():
    return sqlite3.connect(
        DATABASE_NAME,
        timeout=30,
        check_same_thread=False,
        isolation_level=None
    )


# -------------------- INIT --------------------

def init_database():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout = 30000;")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            priority TEXT,
            status TEXT,
            assigned_to TEXT,
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            field_changed TEXT,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT,
            changed_at TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            author TEXT,
            comment TEXT,
            is_internal INTEGER,
            created_at TEXT
        )
        """)

        conn.commit()
        print("Database initialized successfully")


# -------------------- HISTORY --------------------

def log_ticket_history(
    cursor,
    ticket_id,
    field,
    old_value,
    new_value,
    changed_by
):
    cursor.execute(
        """
        INSERT INTO ticket_history
        (ticket_id, field_changed, old_value, new_value, changed_by, changed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ticket_id,
            field,
            old_value,
            new_value,
            changed_by,
            datetime.now().isoformat()
        )
    )


# -------------------- TICKETS --------------------

def create_ticket(
    title,
    description,
    priority="Medium",
    created_by=None
):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.now().isoformat()

            cursor.execute("""
            INSERT INTO tickets
            (title, description, priority, status, assigned_to, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                description,
                priority,
                "Open",
                None,
                created_by,
                now,
                now
            ))

            ticket_id = cursor.lastrowid

            log_ticket_history(
                cursor,
                ticket_id,
                "created",
                None,
                "Open",
                created_by
            )

            conn.commit()
            return get_ticket(ticket_id)

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def update_ticket(
    ticket_id,
    status=None,
    assigned_to=None,
    changed_by=None
):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            ticket = get_ticket(ticket_id)
            if not ticket:
                raise ValueError("Ticket not found")

            updates = {}

            if status and status != ticket.status:
                updates["status"] = (ticket.status, status)

            if assigned_to and assigned_to != ticket.assigned_to:
                updates["assigned_to"] = (ticket.assigned_to, assigned_to)

            for field, (old, new) in updates.items():
                cursor.execute(
                    f"UPDATE tickets SET {field}=?, updated_at=? WHERE id=?",
                    (new, datetime.now().isoformat(), ticket_id)
                )

                log_ticket_history(
                    cursor,
                    ticket_id,
                    field,
                    str(old),
                    str(new),
                    changed_by
                )

            conn.commit()
            return get_ticket(ticket_id)

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def get_ticket(ticket_id) -> Optional[Ticket]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return Ticket(*row)


def get_all_tickets(**filters) -> List[Ticket]:
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM tickets"
    values = []

    if filters:
        query += " WHERE "
        conditions = []
        for k, v in filters.items():
            conditions.append(f"{k}=?")
            values.append(v)
        query += " AND ".join(conditions)

    cursor.execute(query, values)
    rows = cursor.fetchall()
    conn.close()

    return [Ticket(*row) for row in rows]

def delete_ticket(ticket_id: int) -> bool:
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Check if ticket exists
            cursor.execute("SELECT id FROM tickets WHERE id=?", (ticket_id,))
            row = cursor.fetchone()

            if not row:
                return False

            # Delete related data first (important for integrity)
            cursor.execute("DELETE FROM comments WHERE ticket_id=?", (ticket_id,))
            cursor.execute("DELETE FROM ticket_history WHERE ticket_id=?", (ticket_id,))
            cursor.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))

            conn.commit()
            return True

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()



# -------------------- COMMENTS --------------------

def add_comment(ticket_id, author, comment, is_internal=False):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO comments
        (ticket_id, author, comment, is_internal, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            ticket_id,
            author,
            comment,
            int(is_internal),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()


def get_ticket_comments(ticket_id, include_internal=False):
    conn = get_connection()
    cursor = conn.cursor()

    if include_internal:
        cursor.execute(
            "SELECT author, comment, is_internal FROM comments WHERE ticket_id=?",
            (ticket_id,)
        )
    else:
        cursor.execute(
            "SELECT author, comment, is_internal FROM comments WHERE ticket_id=? AND is_internal=0",
            (ticket_id,)
        )

    rows = cursor.fetchall()
    conn.close()

    return [Comment(*row) for row in rows]
