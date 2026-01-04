import sqlite3
from models import Ticket

DATABASE_NAME = "ticket.db"

# INITIALZING THE DATABASE
def init_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'OPEN',
            assigned_to TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("DATABASE INITIALIZED!!!")



# CREATING A SINGLE TICKET
def create_ticket(title, description, priority, assigned_to=None):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tickets (title, description, priority, status, assigned_to)
        VALUES (?, ?, ?, 'OPEN', ?)
    """, (title, description, priority, assigned_to))

    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()

    ticket = Ticket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        priority=priority,
        status="OPEN",
        assigned_to=assigned_to
    )

    print(f"Created {ticket}")
    return ticket

#  DIFFERENT TYPES OF STATUS
VALID_STATUSES = {"OPEN", "IN_PROGRESS", "CLOSED"}


# FOR UPDATING THE STATUS 
def update_status(ticket_id, new_status):
    if new_status not in VALID_STATUSES:
        return "Invalid status"

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET status = ?
        WHERE id = ?
    """, (new_status, ticket_id))

    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        return "Ticket not FOUND"

    conn.close()
    return f"Ticket {ticket_id} status updated to {new_status}"


# IF A STAFF is ASSIGNED
def assign_staff(ticket_id, staff_name):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET assigned_to = ?
        WHERE id = ?
    """, (staff_name, ticket_id))

    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        return "Ticket not FOUND"

    conn.close()
    return f"Ticket {ticket_id} assigned to {staff_name}"


# FOR IDENTIFYNG ALL TICKETS
def get_all_tickets():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, description, priority, status, assigned_to FROM tickets")
    rows = cursor.fetchall()

    conn.close()

    tickets = []
    for row in rows:
        ticket = Ticket(
            ticket_id=row[0],
            title=row[1],
            description=row[2],
            priority=row[3],
            status=row[4],
            assigned_to=row[5]
        )
        tickets.append(ticket)

    return tickets


# FOR PRINTING A SINGLE TICKET
def get_one_ticket(ticket_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, description, priority, status, assigned_to FROM tickets WHERE id = ?",
        (ticket_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return Ticket(
        ticket_id=row[0],
        title=row[1],
        description=row[2],
        priority=row[3],
        status=row[4],
        assigned_to=row[5]
    )

# PRINTING THE DATABASE
def print_all_tickets():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tickets")
    rows = cursor.fetchall()

    conn.close()

    if not rows:
        print("No tickets found.")
        return

    print("\nID | Title | Description | Priority | Status | Assigned To")
    print("-" * 70)

    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")




# FOR CLEARING THE DATABASE
def delete_all_tickets():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tickets")
    conn.commit()

    deleted_count = cursor.rowcount
    conn.close()

    print( f"{deleted_count} tickets deleted successfully")