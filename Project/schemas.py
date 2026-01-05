from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime

# ==========================================
# USER SCHEMAS
# ==========================================

class UserCreate(BaseModel):
    """Schema for creating a user"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(customer|helper|admin)$")
    password: str = Field(..., min_length=6)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "role": "customer",
                "password": "securepass123"
            }
        }


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    email: str
    name: str
    role: str
    created_at: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Schema for login response"""
    message: str
    user: Dict
    token: str  # In real app, this would be JWT


# ==========================================
# TICKET SCHEMAS
# ==========================================

class TicketCreate(BaseModel):
    """Schema for creating a ticket"""
    title: str = Field(..., min_length=1, max_length=200, description="Ticket title")
    description: str = Field(..., min_length=1, description="Detailed description")
    priority: str = Field(default="Medium", pattern="^(Low|Medium|High|Critical)$")
    assigned_to: Optional[str] = Field(None, description="Email of staff to assign (optional)")
    created_by: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Cannot login to dashboard",
                "description": "User reports being unable to login after password reset",
                "priority": "High",
                "created_by": "customer@example.com",
                "assigned_to": "john@support.com"
            }
        }


class TicketUpdate(BaseModel):
    """Schema for updating a ticket"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    priority: Optional[str] = Field(None, pattern="^(Low|Medium|High|Critical)$")
    status: Optional[str] = Field(None, pattern="^(Open|In Progress|Resolved|Closed|On Hold)$")
    assigned_to: Optional[str] = None
    changed_by: str = Field(default="System", description="Who made the change")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "In Progress",
                "priority": "Critical",
                "changed_by": "john@support.com"
            }
        }


class TicketResponse(BaseModel):
    """Schema for ticket response"""
    id: int
    title: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[str]
    created_by: Optional[str]
    created_at: str
    updated_at: str
    resolved_at: Optional[str]
    closed_at: Optional[str]

    class Config:
        from_attributes = True


# ==========================================
# STAFF SCHEMAS
# ==========================================

class StaffCreate(BaseModel):
    """Schema for creating support staff"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="Support Agent", pattern="^(Support Agent|Senior Agent|Team Lead|Manager)$")
    expertise: Optional[str] = None
    max_tickets: int = Field(default=10, ge=1, le=50)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@support.com",
                "name": "John Smith",
                "role": "Senior Agent",
                "expertise": "Authentication, Security",
                "max_tickets": 15
            }
        }


class StaffResponse(BaseModel):
    """Schema for staff response"""
    id: int
    email: str
    name: str
    role: str
    expertise: Optional[str]
    is_active: bool
    max_tickets: int
    created_at: str

    class Config:
        from_attributes = True


# ==========================================
# COMMENT SCHEMAS
# ==========================================

class CommentCreate(BaseModel):
    """Schema for creating a comment"""
    author: str = Field(..., min_length=1)
    comment: str = Field(..., min_length=1, max_length=2000)
    is_internal: bool = Field(default=False, description="Internal note (not visible to customers)")

    class Config:
        json_schema_extra = {
            "example": {
                "author": "john@support.com",
                "comment": "Looking into this issue now",
                "is_internal": True
            }
        }


class CommentResponse(BaseModel):
    """Schema for comment response"""
    id: int
    ticket_id: int
    author: str
    comment: str
    is_internal: bool
    created_at: str

    class Config:
        from_attributes = True


# ==========================================
# CATEGORY SCHEMAS
# ==========================================

class CategoryCreate(BaseModel):
    """Schema for creating a category"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Technical Support",
                "description": "Technical issues and bugs"
            }
        }


class CategoryResponse(BaseModel):
    """Schema for category response"""
    id: int
    name: str
    description: Optional[str]
    parent_id: Optional[int]

    class Config:
        from_attributes = True


# ==========================================
# ANALYTICS SCHEMAS
# ==========================================

class TicketStats(BaseModel):
    """Schema for ticket statistics"""
    total_tickets: int
    active_tickets: int
    unassigned_tickets: int
    by_status: dict
    by_priority: dict


class StaffPerformance(BaseModel):
    """Schema for staff performance"""
    email: str
    name: str
    role: str
    active_tickets: int
    resolved_tickets: int
    total_handled: int


class HelperWorkload(BaseModel):
    """Schema for individual helper workload"""
    email: str
    name: str
    role: str
    active_tickets: int
    resolved_tickets: int
    total_handled: int


class WorkloadReport(BaseModel):
    """Schema for workload report"""
    email: str
    name: str
    role: str
    current_tickets: int
    max_tickets: int
    available_capacity: int


# ==========================================
# GENERAL SCHEMAS
# ==========================================

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    detail: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation successful",
                "detail": "Ticket created with ID 123"
            }
        }


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    database: str
    total_tickets: int


class TagCreate(BaseModel):
    """Schema for creating a tag"""
    tag: str = Field(..., min_length=1, max_length=50, pattern="^[a-zA-Z0-9_-]+$")

    class Config:
        json_schema_extra = {
            "example": {
                "tag": "urgent"
            }
        }


class AssignCategory(BaseModel):
    """Schema for assigning category"""
    category_id: int = Field(..., ge=1)

    class Config:
        json_schema_extra = {
            "example": {
                "category_id": 1
            }
        }
