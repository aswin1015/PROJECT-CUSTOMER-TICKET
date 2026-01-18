import sqlite3
from datetime import datetime
from typing import Optional, List
from threading import Lock
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_NAME = "tickets.db"

# GLOBAL DB LOCK (CRITICAL FOR SQLITE)
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
        resolved_at=None,
        closed_at=None
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
        self.resolved_at = resolved_at
        self.closed_at = closed_at

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
            "closed_at": self.closed_at,
        }


class Comment:
    def __init__(self, id, ticket_id, author, comment, is_internal, created_at):
        self.id = id
        self.ticket_id = ticket_id
        self.author = author
        self.comment = comment
        self.is_internal = is_internal
        self.created_at = created_at

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "author": self.author,
            "comment": self.comment,
            "is_internal": bool(self.is_internal),
            "created_at": self.created_at
        }


# -------------------- CONNECTION --------------------

def get_connection():
    return sqlite3.connect(
        DATABASE_NAME,
        timeout=30,
        check_same_thread=False
    )


# -------------------- INIT --------------------

def init_database():
    with get_connection() as conn:
        cursor = conn.cursor()

        # WAL MODE + TIMEOUT (FIXES LOCKING)
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout = 30000;")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Open',
            assigned_to TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            closed_at TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            field_changed TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT,
            changed_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            comment TEXT NOT NULL,
            is_internal INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """)

        conn.commit()
        logger.info("Database initialized successfully")


# -------------------- HISTORY --------------------

def log_ticket_history(cursor, ticket_id, field, old, new, changed_by):
    cursor.execute(
        """
        INSERT INTO ticket_history
        (ticket_id, field_changed, old_value, new_value, changed_by, changed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ticket_id,
            field,
            old,
            new,
            changed_by,
            datetime.now().isoformat()
        )
    )


# -------------------- TICKETS --------------------

VALID_PRIORITIES = ["Low", "Medium", "High", "Critical"]
VALID_STATUSES = ["Open", "In Progress", "Resolved", "Closed", "On Hold"]


def create_ticket(title, description, priority="Medium", created_by=None):
    if not title.strip():
        raise ValueError("Title cannot be empty")
    if priority not in VALID_PRIORITIES:
        raise ValueError("Invalid priority")

    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO tickets
                (title, description, priority, status, created_by, created_at, updated_at)
                VALUES (?, ?, ?, 'Open', ?, ?, ?)
            """, (title, description, priority, created_by, now, now))

            ticket_id = cursor.lastrowid
            log_ticket_history(cursor, ticket_id, "created", None, "Open", created_by)
            conn.commit()

            return get_ticket(ticket_id)
        finally:
            conn.close()


def update_ticket(ticket_id, status=None, assigned_to=None, changed_by=None):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            ticket = get_ticket(ticket_id)
            if not ticket:
                raise ValueError("Ticket not found")

            now = datetime.now().isoformat()

            if status:
                update_fields = ["status = ?", "updated_at = ?"]
                update_values = [status, now]

                # Handle status transitions
                if status == "Resolved" and ticket.resolved_at is None:
                    update_fields.append("resolved_at = ?")
                    update_values.append(now)

                if status == "Closed" and ticket.closed_at is None:
                    update_fields.append("closed_at = ?")
                    update_values.append(now)

                update_values.append(ticket_id)

                cursor.execute(
                    f"UPDATE tickets SET {', '.join(update_fields)} WHERE id = ?",
                    tuple(update_values)
                )

                log_ticket_history(
                cursor,
                ticket_id,
                "status",
                ticket.status,
                status,
                changed_by
            )

            if assigned_to is not None:
                cursor.execute(
                    "UPDATE tickets SET assigned_to=?, updated_at=? WHERE id=?",
                    (assigned_to, now, ticket_id)
                )
                log_ticket_history(cursor, ticket_id, "assigned_to", ticket.assigned_to, assigned_to, changed_by)

            conn.commit()
            return get_ticket(ticket_id)
        finally:
            conn.close()


def get_ticket(ticket_id) -> Optional[Ticket]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,))
        row = cursor.fetchone()
        return Ticket(*row) if row else None
    finally:
        conn.close()


def get_all_tickets(**filters) -> List[Ticket]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM tickets"
        values = []

        if filters:
            clauses = []
            for k, v in filters.items():
                clauses.append(f"{k}=?")
                values.append(v)
            query += " WHERE " + " AND ".join(clauses)

        cursor.execute(query, values)
        return [Ticket(*row) for row in cursor.fetchall()]
    finally:
        conn.close()


def delete_ticket(ticket_id: int) -> bool:
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM comments WHERE ticket_id=?", (ticket_id,))
            cursor.execute("DELETE FROM ticket_history WHERE ticket_id=?", (ticket_id,))
            cursor.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


# -------------------- COMMENTS --------------------

def add_comment(ticket_id, author, comment, is_internal=False):
    if not comment.strip():
        raise ValueError("Comment cannot be empty")

    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO comments
                (ticket_id, author, comment, is_internal, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (ticket_id, author, comment, int(is_internal), now))

            conn.commit()
            return Comment(cursor.lastrowid, ticket_id, author, comment, is_internal, now)
        finally:
            conn.close()


def get_ticket_comments(ticket_id, include_internal=False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if include_internal:
            cursor.execute("SELECT * FROM comments WHERE ticket_id=?", (ticket_id,))
        else:
            cursor.execute("SELECT * FROM comments WHERE ticket_id=? AND is_internal=0", (ticket_id,))
        return [Comment(*row) for row in cursor.fetchall()]
    finally:
        conn.close()
