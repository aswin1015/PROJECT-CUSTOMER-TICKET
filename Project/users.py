import sqlite3
from datetime import datetime
from typing import Optional, List
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_NAME = "tickets.db"

# User roles
ROLE_CUSTOMER = "customer"
ROLE_HELPER = "helper"
ROLE_ADMIN = "admin"

VALID_ROLES = [ROLE_CUSTOMER, ROLE_HELPER, ROLE_ADMIN]


class User:
    """Represents a user in the system"""
    
    def __init__(self, email: str, name: str, role: str, 
                 user_id: Optional[int] = None, created_at: Optional[str] = None,
                 is_active: bool = True):
        self.id = user_id
        self.email = email
        self.name = name
        self.role = role
        self.is_active = is_active
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
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
    
    # Create index for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    
    conn.commit()
    conn.close()
    logger.info("Users table initialized")


def hash_password(password: str) -> str:
    """Simple password hashing (for demo - use bcrypt or argon2 in production)"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(email: str, name: str, role: str, password: Optional[str] = None) -> User:
    """Create a new user"""
    # Validation
    if not email or '@' not in email:
        raise ValueError("Invalid email address")
    
    if not name or len(name.strip()) == 0:
        raise ValueError("Name cannot be empty")
    
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role. Must be one of {VALID_ROLES}")
    
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        password_hash = hash_password(password) if password else None
        
        cursor.execute("""
            INSERT INTO users (email, name, role, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (email.lower().strip(), name.strip(), role, password_hash, now))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Created user: {name} ({role}) - {email}")
        return User(email, name, role, user_id, now)
    except sqlite3.IntegrityError:
        logger.warning(f"User with email {email} already exists")
        raise ValueError(f"User with email {email} already exists")
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise


def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, email, name, role, created_at, is_active 
            FROM users 
            WHERE email = ?
        """, (email.lower().strip(),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                email=row[1], 
                name=row[2], 
                role=row[3], 
                user_id=row[0], 
                created_at=row[4],
                is_active=bool(row[5])
            )
        return None
    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        return None


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, email, name, role, created_at, is_active 
            FROM users 
            WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                email=row[1], 
                name=row[2], 
                role=row[3], 
                user_id=row[0], 
                created_at=row[4],
                is_active=bool(row[5])
            )
        return None
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}", exc_info=True)
        return None


def get_all_users(role: Optional[str] = None, active_only: bool = True) -> List[User]:
    """Get all users, optionally filtered by role"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        query = "SELECT id, email, name, role, created_at, is_active FROM users WHERE 1=1"
        params = []
        
        if role:
            if role not in VALID_ROLES:
                raise ValueError(f"Invalid role: {role}")
            query += " AND role = ?"
            params.append(role)
        
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append(User(
                email=row[1], 
                name=row[2], 
                role=row[3], 
                user_id=row[0], 
                created_at=row[4],
                is_active=bool(row[5])
            ))
        
        return users
    except Exception as e:
        logger.error(f"Error getting users: {e}", exc_info=True)
        return []


def update_user(email: str, **kwargs) -> Optional[User]:
    """Update user properties"""
    allowed_fields = ['name', 'role', 'is_active']
    
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
    
    if not updates:
        raise ValueError("No valid fields to update")
    
    if 'role' in updates and updates['role'] not in VALID_ROLES:
        raise ValueError(f"Invalid role. Must be one of {VALID_ROLES}")
    
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values()) + [email.lower().strip()]
        
        cursor.execute(f"UPDATE users SET {set_clause} WHERE email=?", values)
        
        if cursor.rowcount == 0:
            conn.close()
            return None
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated user: {email}")
        return get_user_by_email(email)
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        raise


def deactivate_user(email: str) -> bool:
    """Deactivate a user (soft delete)"""
    try:
        user = update_user(email, is_active=False)
        if user:
            logger.info(f"Deactivated user: {email}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deactivating user: {e}", exc_info=True)
        return False


def activate_user(email: str) -> bool:
    """Activate a user"""
    try:
        user = update_user(email, is_active=True)
        if user:
            logger.info(f"Activated user: {email}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error activating user: {e}", exc_info=True)
        return False


def verify_password(email: str, password: str) -> bool:
    """Verify user password"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT password_hash, is_active 
            FROM users 
            WHERE email = ?
        """, (email.lower().strip(),))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False
        
        password_hash, is_active = row
        
        # Check if user is active
        if not is_active:
            logger.warning(f"Login attempt for inactive user: {email}")
            return False
        
        # Verify password
        if password_hash:
            return password_hash == hash_password(password)
        
        return False
    except Exception as e:
        logger.error(f"Error verifying password: {e}", exc_info=True)
        return False


def change_password(email: str, old_password: str, new_password: str) -> bool:
    """Change user password"""
    if not verify_password(email, old_password):
        logger.warning(f"Failed password change attempt for {email}")
        return False
    
    if len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters")
    
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        new_hash = hash_password(new_password)
        cursor.execute("""
            UPDATE users 
            SET password_hash = ? 
            WHERE email = ?
        """, (new_hash, email.lower().strip()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Password changed for user: {email}")
        return True
    except Exception as e:
        logger.error(f"Error changing password: {e}", exc_info=True)
        return False


def is_admin(email: str) -> bool:
    """Check if user is admin"""
    user = get_user_by_email(email)
    return user and user.role == ROLE_ADMIN and user.is_active


def is_helper(email: str) -> bool:
    """Check if user is helper"""
    user = get_user_by_email(email)
    return user and user.role == ROLE_HELPER and user.is_active


def is_customer(email: str) -> bool:
    """Check if user is customer"""
    user = get_user_by_email(email)
    return user and user.role == ROLE_CUSTOMER and user.is_active


def get_all_helpers() -> List[User]:
    """Get all helper users"""
    return get_all_users(role=ROLE_HELPER)


def get_all_customers() -> List[User]:
    """Get all customer users"""
    return get_all_users(role=ROLE_CUSTOMER)


def get_all_admins() -> List[User]:
    """Get all admin users"""
    return get_all_users(role=ROLE_ADMIN)


def setup_demo_users():
    """Create demo users for testing"""
    demo_users = [
        ("admin@system.com", "System Admin", ROLE_ADMIN, "admin123"),
        ("john@support.com", "John Smith", ROLE_HELPER, "helper123"),
        ("sarah@support.com", "Sarah Johnson", ROLE_HELPER, "helper123"),
        ("mike@support.com", "Mike Chen", ROLE_HELPER, "helper123"),
        ("customer1@example.com", "Alice Cooper", ROLE_CUSTOMER, "customer123"),
        ("customer2@example.com", "Bob Wilson", ROLE_CUSTOMER, "customer123"),
    ]
    
    created_count = 0
    for email, name, role, password in demo_users:
        try:
            create_user(email, name, role, password)
            created_count += 1
        except ValueError:
            # User already exists
            pass
        except Exception as e:
            logger.error(f"Error creating demo user {email}: {e}")
    
    if created_count > 0:
        print(f"\nCreated {created_count} demo users!")
        print("\nLogin credentials:")
        print("  Admin: admin@system.com / admin123")
        print("  Helper: john@support.com / helper123")
        print("  Customer: customer1@example.com / customer123")
    else:
        print("\n Demo users already exist")
