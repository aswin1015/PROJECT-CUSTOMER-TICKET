from pydantic import BaseModel, EmailStr, Field, field_validator
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
    is_active: bool = True
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


class PasswordChange(BaseModel):
    """Schema for password change"""
    old_password: str
    new_password: str = Field(..., min_length=6)


# ==========================================
# TICKET SCHEMAS
# ==========================================

class TicketCreate(BaseModel):
    """Schema for creating a ticket"""
    title: str = Field(..., min_length=1, max_length=200, description="Ticket title")
    description: str = Field(..., min_length=1, description="Detailed description")
    priority: str = Field(
        default="Medium",
        pattern="^(Low|Medium|High|Critical)$",
        description="Ticket priority"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Cannot login to dashboard",
                "description": "User reports being unable to login after password reset",
                "priority": "High"
            }
        }


class TicketUpdate(BaseModel):
    """Schema for updating a ticket"""
    status: Optional[str] = Field(
        None,
        pattern="^(Open|In Progress|Resolved|Closed|On Hold)$"
    )
    assigned_to: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "In Progress"
            }
        }


class TicketResponse(BaseModel):
    """Schema for ticket response"""
    id: int
    title: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None

    class Config:
        from_attributes = True


class TicketAssign(BaseModel):
    """Schema for assigning ticket"""
    helper_email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "helper_email": "john@support.com"
            }
        }


# ==========================================
# COMMENT SCHEMAS
# ==========================================

class CommentCreate(BaseModel):
    """Schema for creating a comment (author comes from auth header)"""
    comment: str = Field(..., min_length=1, max_length=2000)
    is_internal: bool = Field(
        default=False, 
        description="Internal note (not visible to customers)"
    )

    class Config:
        json_schema_extra = {
            "example": {
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
# ANALYTICS SCHEMAS
# ==========================================

class TicketStats(BaseModel):
    """Schema for ticket statistics"""
    total_tickets: int
    active_tickets: int
    unassigned_tickets: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]


class StaffPerformance(BaseModel):
    """Schema for staff performance"""
    email: str
    name: str
    role: str
    active_tickets: int
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


class TrendData(BaseModel):
    """Schema for trend data"""
    date: str
    count: int


class ResolutionTimeStats(BaseModel):
    """Schema for resolution time statistics"""
    avg_resolution_hours: float
    avg_response_hours: float = 0.0
    ticket_count: int


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
    message: str
    version: str
    roles: List[str]


class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str
    error_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Resource not found",
                "error_code": "NOT_FOUND"
            }
        }


class SearchRequest(BaseModel):
    """Schema for search request"""
    keyword: str = Field(..., min_length=1, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "login issue"
            }
        }


class DateRangeRequest(BaseModel):
    """Schema for date range queries"""
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator('end_date')
    def validate_date_range(cls, v, info):
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2025-01-01",
                "end_date": "2025-01-31"
            }
        }


class BulkAssignRequest(BaseModel):
    """Schema for bulk ticket assignment"""
    ticket_ids: List[int] = Field(..., min_length=1)
    helper_email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_ids": [1, 2, 3],
                "helper_email": "john@support.com"
            }
        }


class ReassignRequest(BaseModel):
    """Schema for ticket reassignment"""
    new_helper_email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "new_helper_email": "sarah@support.com"
            }
        }
