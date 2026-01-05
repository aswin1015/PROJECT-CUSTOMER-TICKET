from datetime import datetime
from typing import Optional, List

from datetime import datetime
from typing import Optional, List

class User:
    """Represents a user in the system (Customer, Helper, or Admin)"""
    
    def __init__(
        self,
        email: str,
        name: str,
        role: str,
        user_id: Optional[int] = None,
        created_at: Optional[str] = None
    ):
        self.id = user_id
        self.email = email
        self.name = name
        self.role = role  # 'customer', 'helper', or 'admin'
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


class Ticket:
    """Represents a support ticket"""
    
    def __init__(
        self,
        title: str,
        description: str,
        priority: str = "Medium",
        status: str = "Open",
        assigned_to: Optional[str] = None,
        created_by: Optional[str] = None,
        ticket_id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        resolved_at: Optional[str] = None,
        closed_at: Optional[str] = None
    ):
        self.id = ticket_id
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status
        self.assigned_to = assigned_to
        self.created_by = created_by
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.resolved_at = resolved_at
        self.closed_at = closed_at
    
    def to_dict(self):
        """Convert ticket to dictionary"""
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
            "closed_at": self.closed_at
        }
    
    def __str__(self):
        return f"Ticket #{self.id}: {self.title} [{self.status}] - Priority: {self.priority}"


class SupportStaff:
    """Represents a support staff member"""
    
    def __init__(
        self,
        email: str,
        name: str,
        role: str = "Support Agent",
        expertise: Optional[str] = None,
        is_active: bool = True,
        max_tickets: int = 10,
        staff_id: Optional[int] = None,
        created_at: Optional[str] = None
    ):
        self.id = staff_id
        self.email = email
        self.name = name
        self.role = role
        self.expertise = expertise
        self.is_active = is_active
        self.max_tickets = max_tickets
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "expertise": self.expertise,
            "is_active": self.is_active,
            "max_tickets": self.max_tickets,
            "created_at": self.created_at
        }
    
    def __str__(self):
        return f"{self.name} ({self.email}) - {self.role}"


class TicketComment:
    """Represents a comment on a ticket"""
    
    def __init__(
        self,
        ticket_id: int,
        author: str,
        comment: str,
        is_internal: bool = False,
        comment_id: Optional[int] = None,
        created_at: Optional[str] = None
    ):
        self.id = comment_id
        self.ticket_id = ticket_id
        self.author = author
        self.comment = comment
        self.is_internal = is_internal
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "author": self.author,
            "comment": self.comment,
            "is_internal": self.is_internal,
            "created_at": self.created_at
        }
    
    def __str__(self):
        internal_flag = "[INTERNAL]" if self.is_internal else ""
        return f"{internal_flag} {self.author}: {self.comment[:50]}..."


class Category:
    """Represents a ticket category"""
    
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        category_id: Optional[int] = None
    ):
        self.id = category_id
        self.name = name
        self.description = description
        self.parent_id = parent_id
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id
        }
    
    def __str__(self):
        return f"Category: {self.name}"


class TicketHistory:
    """Represents a change in ticket history"""
    
    def __init__(
        self,
        ticket_id: int,
        field_changed: str,
        old_value: Optional[str],
        new_value: Optional[str],
        changed_by: str,
        history_id: Optional[int] = None,
        changed_at: Optional[str] = None
    ):
        self.id = history_id
        self.ticket_id = ticket_id
        self.field_changed = field_changed
        self.old_value = old_value
        self.new_value = new_value
        self.changed_by = changed_by
        self.changed_at = changed_at or datetime.now().isoformat()
    
    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "field_changed": self.field_changed,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at
        }
    
    def __str__(self):
        return f"Ticket #{self.ticket_id}: {self.field_changed} changed from '{self.old_value}' to '{self.new_value}'"
