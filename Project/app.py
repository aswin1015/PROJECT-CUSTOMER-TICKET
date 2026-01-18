from fastapi import FastAPI, HTTPException, Query, Depends, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import logging

from auth import create_access_token, decode_token
from database import *
from users import *
from permissions import *
from schemas import *
from analytics import*

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Customer Support Ticketing System",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# STARTUP
# ======================

@app.on_event("startup")
async def startup():
    init_database()
    init_users_table()
    logger.info("System initialized")

# ======================
# AUTH CORE (COOKIE JWT)
# ======================

def get_current_user(access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(access_token)
    email = payload.get("sub")

    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_email(email)

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user

# ======================
# AUTH ENDPOINTS
# ======================

@app.post("/auth/register", tags=["Authentication"])
async def register(email: str, name: str, password: str, role: str = "customer"):
    if role not in [ROLE_CUSTOMER, ROLE_HELPER, ROLE_ADMIN]:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = create_user(email, name, role, password)
    return user.to_dict()

@app.post("/auth/login", tags=["Authentication"])
async def login(email: str, password: str, response: Response):
    if not verify_password(email, password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = get_user_by_email(email)

    token = create_access_token(
        {
            "sub": user.email,
            "role": user.role
        },
        expires_minutes=3  # AUTO LOGOUT AFTER 3 MIN
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=180,      # 3 minutes
        samesite="lax"
    )

    return {"message": "Login successful"}

@app.post("/auth/logout", tags=["Authentication"])
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

# ======================
# TICKETS
# ======================

@app.post("/tickets", response_model=TicketResponse, tags=["Tickets"])
async def create_ticket_api(
    ticket: TicketCreate,
    user: User = Depends(get_current_user)
):
    t = create_ticket(
        title=ticket.title,
        description=ticket.description,
        priority=ticket.priority,
        created_by=user.email
    )
    return TicketResponse(**t.to_dict())

@app.get("/tickets", response_model=List[TicketResponse], tags=["Tickets"])
async def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    filters = get_user_tickets_filter(user.email)

    if user.role == ROLE_ADMIN:
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority

    tickets = get_all_tickets(**filters)
    return [TicketResponse(**t.to_dict()) for t in tickets]

@app.get("/tickets/{ticket_id}", response_model=TicketResponse, tags=["Tickets"])
async def get_ticket_api(
    ticket_id: int,
    user: User = Depends(get_current_user)
):
    assert_can_view_ticket(user.email, ticket_id)

    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketResponse(**ticket.to_dict())

@app.put("/tickets/{ticket_id}", response_model=TicketResponse, tags=["Tickets"])
async def update_ticket_api(
    ticket_id: int,
    update: TicketUpdate,
    user: User = Depends(get_current_user)
):
    assert_can_update_ticket(user.email, ticket_id)

    data = {k: v for k, v in update.model_dump().items() if v is not None}

    ticket = update_ticket(ticket_id, changed_by=user.email, **data)
    return TicketResponse(**ticket.to_dict())

@app.delete("/tickets/{ticket_id}", tags=["Tickets"])
async def delete_ticket_api(
    ticket_id: int,
    user: User = Depends(get_current_user)
):
    assert_is_admin(user.email)

    if not delete_ticket(ticket_id):
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {"message": "Deleted"}

# ======================
# COMMENTS
# ======================

@app.post("/tickets/{ticket_id}/comments", response_model=CommentResponse, tags=["Comments"])
async def add_comment_api(
    ticket_id: int,
    comment: CommentCreate,
    user: User = Depends(get_current_user)
):
    allowed = (
        can_add_internal_comment(user.email, ticket_id)
        if comment.is_internal
        else can_add_comment(user.email, ticket_id)
    )

    if not allowed:
        raise HTTPException(status_code=403, detail="Permission denied")

    c = add_comment(
        ticket_id,
        user.email,
        comment.comment,
        comment.is_internal
    )
    return CommentResponse(**c.to_dict())

@app.get("/tickets/{ticket_id}/comments", response_model=List[CommentResponse], tags=["Comments"])
async def list_comments_api(
    ticket_id: int,
    user: User = Depends(get_current_user)
):
    assert_can_view_ticket(user.email, ticket_id)
    include_internal = can_view_internal_comments(user.email)

    comments = get_ticket_comments(ticket_id, include_internal)
    return [CommentResponse(**c.to_dict()) for c in comments]

# ======================
# ASSIGNMENT
# ======================

@app.put("/tickets/{ticket_id}/assign", response_model=TicketResponse, tags=["Assignment"])
async def assign_ticket_api(
    ticket_id: int,
    helper_email: str,
    user: User = Depends(get_current_user)
):
    assert_is_admin(user.email)

    if not is_helper(helper_email):
        raise HTTPException(status_code=400, detail="Not a helper")

    ticket = update_ticket(
        ticket_id,
        assigned_to=helper_email,
        changed_by=user.email
    )
    return TicketResponse(**ticket.to_dict())

# ======================
# USERS
# ======================

@app.get("/users", tags=["Users"])
async def list_users(user: User = Depends(get_current_user)):
    assert_is_admin(user.email)
    return [u.to_dict() for u in get_all_users()]

@app.get("/users/helpers", tags=["Users"])
async def list_helpers(user: User = Depends(get_current_user)):
    assert_is_admin(user.email)
    return [h.to_dict() for h in get_all_helpers()]

# ======================
# ANALYTICS
# =====================

@app.get("/analytics/stats", tags=["Analytics"])
async def get_statistics(user: User = Depends(get_current_user)):
    require_permission(user.email, "view_analytics")
    return get_ticket_stats()

@app.get("/analytics/performance", tags=["Analytics"])
async def get_performance(user: User = Depends(get_current_user)):
    require_permission(user.email, "view_analytics")
    return get_staff_performance()

@app.get("/analytics/resolution-time", tags=["Analytics"])
async def get_resolution_time(user: User = Depends(get_current_user)):
    require_permission(user.email, "view_analytics")

    return {
        "avg_resolution_hours": get_average_resolution_time(),
        "avg_response_hours": get_response_time_stats().get("avg_response_hours", 0.0)
    }

# ======================
# HEALTH
# ======================

@app.get("/", tags=["Health"])
async def health():
    return {"status": "ok"}
