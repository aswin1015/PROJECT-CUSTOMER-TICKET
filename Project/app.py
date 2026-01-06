from fastapi import FastAPI, HTTPException, Query, Path, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import logging

# Import our modules
from database import *
from allocation import get_allocation_report, reassign_ticket, get_available_staff, auto_assign_ticket
from analytics import (
    get_ticket_stats, get_staff_performance, search_tickets,
    get_average_resolution_time, get_response_time_stats
)
from schemas import *
from users import *
from permissions import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# FASTAPI APP
# ==========================================

app = FastAPI(
    title="Customer Support Ticketing System with Roles",
    description="Multi-role ticketing system: Customer, Helper, Admin",
    version="2.0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database and users"""
    init_database()
    init_users_table()
    logger.info("System initialized successfully")


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_current_user(x_user_email: str) -> User:
    """Get current user from header (simplified auth)"""
    user = get_user_by_email(x_user_email)
    if not user:
        logger.warning(f"User not found: {x_user_email}")
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {x_user_email}")
        raise HTTPException(status_code=401, detail="User account is inactive")
    return user


# ==========================================
# AUTH ENDPOINTS
# ==========================================

@app.post("/auth/register", tags=["Authentication"])
async def register_user(
    email: str,
    name: str,
    password: str,
    role: str = "customer"
):
    """Register a new user (customer by default)"""
    try:
        if role not in [ROLE_CUSTOMER, ROLE_HELPER, ROLE_ADMIN]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        user = create_user(email, name, role, password)
        return {
            "message": "User registered successfully",
            "user": user.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/auth/login", tags=["Authentication"])
async def login(email: str, password: str):
    """Login (simplified - just returns user info)"""
    if verify_password(email, password):
        user = get_user_by_email(email)
        return {
            "message": "Login successful",
            "user": user.to_dict(),
            "token": email  # In real app, use JWT
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/auth/change-password", tags=["Authentication"])
async def change_password_endpoint(
    old_password: str,
    new_password: str,
    x_user_email: str = Header(...)
):
    """Change user password"""
    user = get_current_user(x_user_email)
    
    try:
        if change_password(user.email, old_password, new_password):
            return {"message": "Password changed successfully"}
        raise HTTPException(status_code=400, detail="Invalid old password")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# TICKET ENDPOINTS
# ==========================================

@app.post("/tickets", response_model=TicketResponse, status_code=201, tags=["Tickets"])
async def create_new_ticket(
    ticket: TicketCreate,
    x_user_email: str = Header(...)
):
    """Create a new ticket"""
    user = get_current_user(x_user_email)

    try:
        new_ticket = create_ticket(
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority,
            created_by=user.email
        )
        
        logger.info(f"Ticket #{new_ticket.id} created by {user.email}")
        return TicketResponse(**new_ticket.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tickets", response_model=List[TicketResponse], tags=["Tickets"])
async def list_tickets(
    x_user_email: str = Header(...),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """
    List tickets based on user role:
    - Customer: Only their tickets
    - Helper: Only assigned tickets
    - Admin: All tickets (can filter)
    """
    user = get_current_user(x_user_email)
    
    try:
        # Apply role-based filtering
        filters = get_user_tickets_filter(user.email)
        
        # Admin can override with additional filters
        if user.role == ROLE_ADMIN:
            if status:
                filters['status'] = status
            if priority:
                filters['priority'] = priority
        
        tickets = get_all_tickets(**filters)
        tickets = tickets[:limit]
        
        return [TicketResponse(**t.to_dict()) for t in tickets]
    except Exception as e:
        logger.error(f"Error listing tickets: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tickets/{ticket_id}", response_model=TicketResponse, tags=["Tickets"])
async def get_ticket_details(
    ticket_id: int,
    x_user_email: str = Header(...)
):
    """Get ticket details (permission checked)"""
    user = get_current_user(x_user_email)
    
    try:
        # Check permission
        assert_can_view_ticket(user.email, ticket_id)
        
        ticket = get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return TicketResponse(**ticket.to_dict())
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.put("/tickets/{ticket_id}", response_model=TicketResponse, tags=["Tickets"])
async def update_ticket_endpoint(
    ticket_id: int,
    ticket_update: TicketUpdate,
    x_user_email: str = Header(...)
):
    """Update ticket (Helper/Admin only)"""
    user = get_current_user(x_user_email)

    try:
        assert_can_update_ticket(user.email, ticket_id)

        update_data = {
            k: v for k, v in ticket_update.model_dump().items()
            if v is not None
        }

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        updated_ticket = update_ticket(
            ticket_id=ticket_id,
            changed_by=user.email,
            **update_data
        )

        logger.info(f"Ticket #{ticket_id} updated by {user.email}")
        return TicketResponse(**updated_ticket.to_dict())
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/tickets/{ticket_id}", tags=["Tickets"])
async def delete_ticket_endpoint(
    ticket_id: int,
    x_user_email: str = Header(...)
):
    """Delete ticket (Admin only)"""
    user = get_current_user(x_user_email)
    
    try:
        assert_is_admin(user.email)
        
        success = delete_ticket(ticket_id)
        if not success:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        logger.info(f"Ticket #{ticket_id} deleted by {user.email}")
        return {"message": "Ticket deleted successfully"}
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==========================================
# COMMENT ENDPOINTS
# ==========================================

@app.post("/tickets/{ticket_id}/comments", response_model=CommentResponse, tags=["Comments"])
async def add_comment_to_ticket(
    ticket_id: int,
    comment: CommentCreate,
    x_user_email: str = Header(...)
):
    """
    Add comment to ticket.
    - Customer: Can add public comments to their tickets
    - Helper: Can add public/internal comments to assigned tickets
    - Admin: Can add comments to any ticket
    """
    user = get_current_user(x_user_email)
    
    try:
        # Check permission
        require_permission(user.email, "add_comment", ticket_id=ticket_id)
        
        # Customers cannot add internal comments
        if user.role == ROLE_CUSTOMER and comment.is_internal:
            raise HTTPException(status_code=403, detail="Customers cannot add internal notes")
        
        new_comment = add_comment(
            ticket_id=ticket_id,
            author=user.email,
            comment=comment.comment,
            is_internal=comment.is_internal
        )
        
        if not new_comment:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        logger.info(f"Comment added to ticket #{ticket_id} by {user.email}")
        return CommentResponse(**new_comment.to_dict())
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tickets/{ticket_id}/comments", response_model=List[CommentResponse], tags=["Comments"])
async def get_ticket_comments_endpoint(
    ticket_id: int,
    x_user_email: str = Header(...)
):
    """
    Get comments for ticket.
    - Customer: Only public comments
    - Helper/Admin: All comments (including internal)
    """
    user = get_current_user(x_user_email)
    
    try:
        # Check permission to view ticket
        assert_can_view_ticket(user.email, ticket_id)
        
        # Determine if user can see internal comments
        include_internal = can_view_internal_comments(user.email)
        
        comments = get_ticket_comments(ticket_id, include_internal=include_internal)
        return [CommentResponse(**c.to_dict()) for c in comments]
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==========================================
# ASSIGNMENT ENDPOINTS (Admin only)
# ==========================================

@app.put("/tickets/{ticket_id}/assign", response_model=TicketResponse, tags=["Assignment"])
async def assign_ticket_endpoint(
    ticket_id: int,
    helper_email:str,
    x_user_email: str = Header(...)
):
    """Assign ticket to helper (Admin only)"""
    user = get_current_user(x_user_email)

    try:
        assert_is_admin(user.email)

        # Check if the helper_email is actually a helper
        # helper_user = get_current_user(assignment.helper_email)
        if not is_helper(helper_email):
            raise ValueError(f"{helper_email} is not a helper")

        updated_ticket = update_ticket(
            ticket_id=ticket_id,
            assigned_to= helper_email,
            changed_by=user.email
        )

        logger.info(f"Ticket #{ticket_id} assigned to {helper_email} by {user.email}")
        return TicketResponse(**updated_ticket.to_dict())

    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.post("/tickets/{ticket_id}/auto-assign", response_model=TicketResponse, tags=["Assignment"])
async def auto_assign_ticket_endpoint(
    ticket_id: int,
    x_user_email: str = Header(...)
):
    """Auto-assign ticket to helper with most capacity (Admin only)"""
    user = get_current_user(x_user_email)
    
    try:
        assert_is_admin(user.email)
        
        helper_email = auto_assign_ticket(ticket_id, changed_by=user.email)
        
        if not helper_email:
            raise HTTPException(status_code=400, detail="No helpers available or all at capacity")
        
        ticket = get_ticket(ticket_id)
        logger.info(f"Ticket #{ticket_id} auto-assigned to {helper_email}")
        return TicketResponse(**ticket.to_dict())
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.put("/tickets/{ticket_id}/reassign", response_model=TicketResponse, tags=["Assignment"])
async def reassign_ticket_endpoint(
    ticket_id: int,
    reassignment: ReassignRequest,
    x_user_email: str = Header(...)
):
    """Reassign ticket to different helper (Admin only)"""
    user = get_current_user(x_user_email)
    
    try:
        assert_is_admin(user.email)
        
        if reassign_ticket(ticket_id, reassignment.new_helper_email, user.email):
            ticket = get_ticket(ticket_id)
            return TicketResponse(**ticket.to_dict())
        
        raise HTTPException(status_code=404, detail="Ticket not found")
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/staff/workload", tags=["Staff"])
async def get_workload(x_user_email: str = Header(...)):
    """Get staff workload (Helper can see own, Admin sees all)"""
    user = get_current_user(x_user_email)
    
    try:
        require_permission(user.email, "view_workload")
        
        staff_list = get_available_staff()
        
        # Helper can only see their own workload
        if user.role == ROLE_HELPER:
            staff_list = [s for s in staff_list if s['email'] == user.email]
        
        return staff_list
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==========================================
# USER MANAGEMENT (Admin only)
# ==========================================

@app.get("/users", tags=["Users"])
async def list_users_endpoint(
    role: Optional[str] = Query(None),
    x_user_email: str = Header(...)
):
    """List all users (Admin only)"""
    user = get_current_user(x_user_email)
    
    try:
        assert_is_admin(user.email)
        
        users = get_all_users(role=role)
        return [u.to_dict() for u in users]
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/users/helpers", tags=["Users"])
async def list_helpers(x_user_email: str = Header(...)):
    """List all helpers (Admin only)"""
    user = get_current_user(x_user_email)
    
    try:
        assert_is_admin(user.email)
        
        helpers = get_all_helpers()
        return [h.to_dict() for h in helpers]
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==========================================
# ANALYTICS (Admin/Helper)
# ==========================================

@app.get("/analytics/stats", tags=["Analytics"])
async def get_statistics(x_user_email: str = Header(...)):
    """Get ticket statistics (Admin only)"""
    user = get_current_user(x_user_email)
    
    try:
        assert_is_admin(user.email)
        
        stats = get_ticket_stats()
        return stats
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/analytics/performance", tags=["Analytics"])
async def get_performance(x_user_email: str = Header(...)):
    """Get staff performance (Admin only)"""
    user = get_current_user(x_user_email)
    
    try:
        assert_is_admin(user.email)
        
        performance = get_staff_performance()
        return performance
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/analytics/resolution-time", tags=["Analytics"])
async def get_resolution_time(x_user_email: str = Header(...)):
    """Get average resolution time (Admin only)"""
    user = get_current_user(x_user_email)
    
    try:
        assert_is_admin(user.email)
        
        avg_hours = get_average_resolution_time()
        response_stats = get_response_time_stats()
        
        return {
            "avg_resolution_hours": avg_hours,
            "avg_response_hours": response_stats.get("avg_response_hours", 0.0)
        }
    except PermissionDenied as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/search", tags=["Search"])
async def search_tickets_endpoint(
    keyword: str = Query(..., min_length=1),
    x_user_email: str = Header(...)
):
    """Search tickets by keyword"""
    user = get_current_user(x_user_email)
    
    try:
        all_results = search_tickets(keyword)
        
        # Filter results based on user permissions
        filtered_results = []
        for ticket in all_results:
            if can_view_ticket(user.email, ticket['id']):
                filtered_results.append(ticket)
        
        return filtered_results
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Customer Support Ticketing System API",
        "version": "2.0.1",
        "roles": [ROLE_CUSTOMER, ROLE_HELPER, ROLE_ADMIN]
    }


@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check_detailed():
    """Detailed health check"""
    return {
        "status": "healthy",
        "message": "All systems operational",
        "version": "2.0.1",
        "roles": [ROLE_CUSTOMER, ROLE_HELPER, ROLE_ADMIN]
    }
