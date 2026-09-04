"""Customer Authentication API routes for Nyxeris.
Handles user registration, login, session validation, profile updates,
and customer order tracking.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Request, Response, Cookie, Depends
from pydantic import BaseModel, EmailStr, Field

from services.auth_service import (
    create_customer,
    authenticate_customer,
    generate_session_token,
    verify_session_token,
    get_customer_by_id,
    update_customer_profile,
    get_customer_orders
)
from database import get_db_connection

router = APIRouter(prefix="/api/auth", tags=["Customer Authentication"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "United States"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


# ---------------------------------------------------------------------------
# Auth Dependency
# ---------------------------------------------------------------------------

def get_current_customer(request: Request) -> Optional[Dict[str, Any]]:
    """Extracts customer session from cookie or Authorization header."""
    token = request.cookies.get("nyxeris_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            
    if not token:
        return None
        
    payload = verify_session_token(token)
    if not payload:
        return None
        
    customer = get_customer_by_id(payload["sub"])
    if customer:
        customer.pop("password_hash", None)
    return customer


def require_customer(request: Request) -> Dict[str, Any]:
    """Dependency that ensures customer is authenticated."""
    customer = get_current_customer(request)
    if not customer:
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in.")
    return customer


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.post("/register")
async def register_customer(payload: RegisterRequest, response: Response):
    """Creates a new customer account and issues an authenticated session."""
    try:
        customer = create_customer(
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            phone=payload.phone,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            postal_code=payload.postal_code,
            country=payload.country
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    token = generate_session_token(customer["id"], customer["email"])
    
    # Set secure cookie
    response.set_cookie(
        key="nyxeris_session",
        value=token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=False  # Allows localhost and HTTPS
    )
    
    return {
        "status": "success",
        "message": "Account created successfully.",
        "token": token,
        "customer": customer
    }


@router.post("/login")
async def login_customer(payload: LoginRequest, response: Response):
    """Authenticates customer credentials and establishes a session."""
    customer = authenticate_customer(payload.email, payload.password)
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    token = generate_session_token(customer["id"], customer["email"])
    
    response.set_cookie(
        key="nyxeris_session",
        value=token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=False
    )
    
    return {
        "status": "success",
        "message": f"Welcome back, {customer['full_name']}!",
        "token": token,
        "customer": customer
    }


@router.get("/me")
async def get_my_profile(request: Request):
    """Returns profile for currently authenticated customer."""
    customer = get_current_customer(request)
    if not customer:
        return {"authenticated": False, "customer": None}
    return {"authenticated": True, "customer": customer}


@router.post("/logout")
async def logout_customer(response: Response):
    """Clears customer session cookie."""
    response.delete_cookie(key="nyxeris_session")
    return {"status": "success", "message": "Signed out successfully."}


@router.get("/orders")
async def get_my_orders(customer: Dict[str, Any] = Depends(require_customer)):
    """Retrieves all past orders placed by this customer."""
    orders = get_customer_orders(customer["id"], customer["email"])
    return {
        "status": "success",
        "customer_id": customer["id"],
        "count": len(orders),
        "orders": orders
    }


@router.post("/update-profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    customer: Dict[str, Any] = Depends(require_customer)
):
    """Updates saved shipping address and contact info."""
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    updated = update_customer_profile(customer["id"], updates)
    return {
        "status": "success",
        "message": "Profile updated successfully.",
        "customer": updated
    }


@router.get("/lookup-order")
async def quick_order_lookup(order_id: str, email: Optional[str] = None):
    """Non-authenticated quick order status lookup (replaces crude browser prompts)."""
    clean_id = order_id.strip().upper()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE UPPER(order_id) = ?", (clean_id,))
    order_row = c.fetchone()
    
    if not order_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found. Please check your order ID.")
        
    order = dict(order_row)
    
    # If email provided, verify match
    if email and email.strip():
        if order["customer_email"].strip().lower() != email.strip().lower():
            conn.close()
            raise HTTPException(status_code=403, detail="Email does not match this order.")
            
    c.execute("SELECT * FROM order_items WHERE order_id = ?", (order["order_id"],))
    items = [dict(it) for it in c.fetchall()]
    conn.close()
    
    order["items"] = items
    return {
        "status": "success",
        "order": order
    }
