import requests

BASE_URL = "http://127.0.0.1:8000"

session = requests.Session()

# ---------------- AUTH ----------------

def register(email, name, password, role):
    return session.post(
        f"{BASE_URL}/auth/register",
        params={
            "email": email,
            "name": name,
            "password": password,
            "role": role
        }
    )

def login(email, password):
    return session.post(
        f"{BASE_URL}/auth/login",
        params={"email": email, "password": password}
    )

def logout():
    return session.post(f"{BASE_URL}/auth/logout")

# ---------------- TICKETS ----------------

def get_tickets():
    return session.get(f"{BASE_URL}/tickets")

def create_ticket(title, description, priority):
    return session.post(
        f"{BASE_URL}/tickets",
        json={
            "title": title,
            "description": description,
            "priority": priority
        }
    )

def update_ticket(ticket_id, status=None, assigned_to=None):
    return session.put(
        f"{BASE_URL}/tickets/{ticket_id}",
        json={
            "status": status,
            "assigned_to": assigned_to
        }
    )

def assign_ticket(ticket_id, helper_email):
    return session.put(
        f"{BASE_URL}/tickets/{ticket_id}/assign",
        params={"helper_email": helper_email}
    )

def delete_ticket(ticket_id):
    return session.delete(f"{BASE_URL}/tickets/{ticket_id}")

# ---------------- USERS ----------------
def get_me():
    return session.get(f"{BASE_URL}/auth/me")

def get_users():
    return session.get(f"{BASE_URL}/users")

def get_helpers():
    return session.get(f"{BASE_URL}/users/helpers")

# ---------------- ANALYTICS ----------------

def get_stats():
    return session.get(f"{BASE_URL}/analytics/stats")

def get_performance():
    return session.get(f"{BASE_URL}/analytics/performance")

def get_resolution_time():
    return session.get(f"{BASE_URL}/analytics/resolution-time")


# =======================
# COMMENTS
# =======================

def get_comments(ticket_id):
    return session.get(f"{BASE_URL}/tickets/{ticket_id}/comments")

def add_comment(ticket_id, comment, is_internal=False):
    return session.post(
        f"{BASE_URL}/tickets/{ticket_id}/comments",
        json={
            "comment": comment,
            "is_internal": is_internal
        }
    )