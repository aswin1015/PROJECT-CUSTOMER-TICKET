import sqlite3
from datetime import datetime
from typing import Optional, List
import hashlib

DATABASE_NAME = "tickets.db"

# User roles
ROLE_CUSTOMER = "customer"
ROLE_HELPER = "helper"
ROLE_ADMIN = "admin"

class User:
    """Represents a user in the system"""
    
    def __init__(self, email: str, name: str, role: str, 
                 user_id: Optional[int] = None, created_at: Optional[str] = None):
        self.id = user_id
        self.email = email
        self.name = name
        self.role = role
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at
        }
    
    def __str__(self):
        return f"{self.name} ({self.email}) - {self.role}"


def init_users_table():
    """Initialize users table"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            password_hash TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            
            CHECK (role IN ('customer', 'helper', 'admin'))
        )
    """)
    
    conn.commit()
    conn.close()
    print("Users table initialized")


def hash_password(password: str) -> str:
    """Simple password hashing (for demo - use proper hashing in production)"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(email: str, name: str, role: str, password: Optional[str] = None) -> User:
    """Create a new user"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        password_hash = hash_password(password) if password else None
        
        cursor.execute("""
            INSERT INTO users (email, name, role, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (email, name, role, password_hash, now))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✓ Created user: {name} ({role})")
        return User(email, name, role, user_id, now)
    except sqlite3.IntegrityError:
        print(f"✗ User with email {email} already exists")
        raise
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        raise


def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, email, name, role, created_at FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(email=row[1], name=row[2], role=row[3], user_id=row[0], created_at=row[4])
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def get_all_users(role: Optional[str] = None) -> List[User]:
    """Get all users, optionally filtered by role"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        if role:
            cursor.execute("SELECT id, email, name, role, created_at FROM users WHERE role = ? AND is_active = 1", (role,))
        else:
            cursor.execute("SELECT id, email, name, role, created_at FROM users WHERE is_active = 1")
        
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append(User(email=row[1], name=row[2], role=row[3], user_id=row[0], created_at=row[4]))
        
        return users
    except Exception as e:
        print(f"Error getting users: {e}")
        return []


def verify_password(email: str, password: str) -> bool:
    """Verify user password"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return row[0] == hash_password(password)
        return False
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False


def is_admin(email: str) -> bool:
    """Check if user is admin"""
    user = get_user_by_email(email)
    return user and user.role == ROLE_ADMIN


def is_helper(email: str) -> bool:
    """Check if user is helper"""
    user = get_user_by_email(email)
    return user and user.role == ROLE_HELPER


def is_customer(email: str) -> bool:
    """Check if user is customer"""
    user = get_user_by_email(email)
    return user and user.role == ROLE_CUSTOMER


def get_all_helpers() -> List[User]:
    """Get all helper users"""
    return get_all_users(role=ROLE_HELPER)


def get_all_customers() -> List[User]:
    """Get all customer users"""
    return get_all_users(role=ROLE_CUSTOMER)


def setup_demo_users():
    """Create demo users for testing"""
    try:
        # Create admin
        create_user("admin@system.com", "System Admin", ROLE_ADMIN, "admin123")
        
        # Create helpers
        create_user("john@support.com", "John Smith", ROLE_HELPER, "helper123")
        create_user("sarah@support.com", "Sarah Johnson", ROLE_HELPER, "helper123")
        create_user("mike@support.com", "Mike Chen", ROLE_HELPER, "helper123")
        
        # Create customers
        create_user("customer1@example.com", "Alice Cooper", ROLE_CUSTOMER, "customer123")
        create_user("customer2@example.com", "Bob Wilson", ROLE_CUSTOMER, "customer123")
        
        print("\n Demo users created!")
        print("\nLogin credentials:")
        print("  Admin: admin@system.com / admin123")
        print("  Helper: john@support.com / helper123")
        print("  Customer: customer1@example.com / customer123")
    except Exception as e:
        print(f"Note: Some users may already exist - {e}")