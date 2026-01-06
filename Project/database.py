import sqlite3
from datetime import datetime
from typing import Optional, List
from threading import Lock
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    def __repr__(self):
        return f"Ticket(id={self.id}, title={self.title}, status={self.status})"


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
            changed_at TEXT NOT NULL,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            comment TEXT NOT NULL,
            is_internal INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id)
        )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_assigned ON tickets(assigned_to)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_created_by ON tickets(created_by)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_ticket ON comments(ticket_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_ticket ON ticket_history(ticket_id)")

        conn.commit()
        logger.info("Database initialized successfully")


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

VALID_PRIORITIES = ["Low", "Medium", "High", "Critical"]
VALID_STATUSES = ["Open", "In Progress", "Resolved", "Closed", "On Hold"]


def create_ticket(
    title,
    description,
    priority="Medium",
    created_by=None
):
    # Validation
    if not title or len(title.strip()) == 0:
        raise ValueError("Title cannot be empty")
    
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority. Must be one of {VALID_PRIORITIES}")

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
                title.strip(),
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
                created_by or "System"
            )

            conn.commit()
            logger.info(f"Created ticket #{ticket_id}")
            return get_ticket(ticket_id)

        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating ticket: {e}", exc_info=True)
            raise
        finally:
            conn.close()


def update_ticket(
    ticket_id,
    status=None,
    assigned_to=None,
    changed_by=None
):
    # Validation
    if status and status not in VALID_STATUSES:
        raise ValueError(f"Invalid status. Must be one of {VALID_STATUSES}")

    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            ticket = get_ticket(ticket_id)
            if not ticket:
                raise ValueError("Ticket not found")

            updates = {}
            now = datetime.now().isoformat()

            if status and status != ticket.status:
                updates["status"] = (ticket.status, status)

            if assigned_to is not None and assigned_to != ticket.assigned_to:
                updates["assigned_to"] = (ticket.assigned_to, assigned_to)

            for field, (old, new) in updates.items():
                cursor.execute(
                    f"UPDATE tickets SET {field}=?, updated_at=? WHERE id=?",
                    (new, now, ticket_id)
                )

                log_ticket_history(
                    cursor,
                    ticket_id,
                    field,
                    str(old) if old else None,
                    str(new) if new else None,
                    changed_by or "System"
                )

            # Set resolved_at when status changes to Resolved
            if status == "Resolved" and ticket.status != "Resolved":
                cursor.execute(
                    "UPDATE tickets SET resolved_at=? WHERE id=?",
                    (now, ticket_id)
                )
                logger.info(f"Ticket #{ticket_id} resolved at {now}")

            # Set closed_at when status changes to Closed
            if status == "Closed" and ticket.status != "Closed":
                cursor.execute(
                    "UPDATE tickets SET closed_at=? WHERE id=?",
                    (now, ticket_id)
                )
                logger.info(f"Ticket #{ticket_id} closed at {now}")

            conn.commit()
            return get_ticket(ticket_id)

        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating ticket: {e}", exc_info=True)
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
        conditions = []
        for k, v in filters.items():
            # Whitelist allowed filter fields
            if k in ['status', 'priority', 'assigned_to', 'created_by']:
                conditions.append(f"{k}=?")
                values.append(v)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC"

    cursor.execute(query, values)
    rows = cursor.fetchall()
    conn.close()

    return [Ticket(*row) for row in rows]


def delete_ticket(ticket_id: int) -> bool:
    conn = None
    try:
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()

            # Check if ticket exists
            cursor.execute("SELECT id FROM tickets WHERE id=?", (ticket_id,))
            if not cursor.fetchone():
                return False

            # Delete related data first (important for integrity)
            cursor.execute("DELETE FROM comments WHERE ticket_id=?", (ticket_id,))
            cursor.execute("DELETE FROM ticket_history WHERE ticket_id=?", (ticket_id,))
            cursor.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))

            conn.commit()
            logger.info(f"Deleted ticket #{ticket_id}")
            return True

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting ticket: {e}", exc_info=True)
        raise

    finally:
        if conn:
            conn.close()


# -------------------- COMMENTS --------------------

def add_comment(ticket_id, author, comment, is_internal=False):
    # Validation
    if not comment or len(comment.strip()) == 0:
        raise ValueError("Comment cannot be empty")

    # Check if ticket exists
    if not get_ticket(ticket_id):
        raise ValueError(f"Ticket #{ticket_id} not found")

    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.now().isoformat()

            cursor.execute("""
            INSERT INTO comments
            (ticket_id, author, comment, is_internal, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (
                ticket_id,
                author,
                comment.strip(),
                int(is_internal),
                now
            ))

            comment_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Added comment to ticket #{ticket_id}")

            return Comment(
                comment_id,
                ticket_id,
                author,
                comment.strip(),
                is_internal,
                now
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding comment: {e}", exc_info=True)
            raise
        finally:
            conn.close()


def get_ticket_comments(ticket_id, include_internal=False):
    conn = get_connection()
    cursor = conn.cursor()

    if include_internal:
        cursor.execute("""
        SELECT id, ticket_id, author, comment, is_internal, created_at
        FROM comments
        WHERE ticket_id=?
        ORDER BY created_at ASC
        """, (ticket_id,))
    else:
        cursor.execute("""
        SELECT id, ticket_id, author, comment, is_internal, created_at
        FROM comments
        WHERE ticket_id=? AND is_internal=0
        ORDER BY created_at ASC
        """, (ticket_id,))

    rows = cursor.fetchall()
    conn.close()

    return [Comment(*row) for row in rows]
