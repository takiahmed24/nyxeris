"""Customer Authentication and Session Management Service for Nyxeris.
Provides secure password hashing, session tokens, customer registration,
login verification, profile management, and unified order history.
"""

import hashlib
import hmac
import secrets
import json
import base64
import time
import uuid
from typing import Optional, Dict, Any, List

from config import settings
from database import get_db_connection

# Secret for HMAC token signing (falls back to a stable deterministic secret derived from settings)
AUTH_SECRET = getattr(settings, "AUTH_SECRET", "nyxeris_lux_auth_secret_2026_salt")
TOKEN_EXPIRY_SECONDS = 30 * 24 * 3600  # 30 days session validity


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    return f"{salt}:{key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a password against the stored salt:hash string."""
    try:
        salt, key_hex = stored_hash.split(":", 1)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        )
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


def generate_session_token(customer_id: str, email: str) -> str:
    """Generates a tamper-proof cryptographically signed session token."""
    payload = {
        "sub": customer_id,
        "email": email.strip().lower(),
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
        "nonce": secrets.token_hex(8)
    }
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    
    signature = hmac.new(
        AUTH_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{signature}"


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies a signed session token and returns the payload if valid and unexpired."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, signature = token.strip().split(".", 1)
        expected_sig = hmac.new(
            AUTH_SECRET.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
            
        # Add padding back to base64
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
        
        if payload.get("exp", 0) < time.time():
            return None  # Expired
            
        return payload
    except Exception:
        return None


def get_customer_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves customer record by email."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM customers WHERE LOWER(email) = LOWER(?)", (email.strip(),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_customer_by_id(customer_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves customer record by ID."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def create_customer(
    full_name: str,
    email: str,
    password: str,
    phone: Optional[str] = None,
    address_line1: Optional[str] = None,
    address_line2: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    country: Optional[str] = "United States"
) -> Dict[str, Any]:
    """Registers a new customer and returns customer data dict."""
    clean_email = email.strip().lower()
    if get_customer_by_email(clean_email):
        raise ValueError("An account with this email address already exists.")
        
    customer_id = f"cust_{uuid.uuid4().hex[:12]}"
    pwd_hash = hash_password(password)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO customers (
            id, email, password_hash, full_name, phone,
            address_line1, address_line2, city, state, postal_code, country
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id, clean_email, pwd_hash, full_name.strip(), phone or "",
        address_line1 or "", address_line2 or "", city or "", state or "",
        postal_code or "", country or "United States"
    ))
    
    # Retroactively link any existing orders placed under this email address
    c.execute("UPDATE orders SET customer_id = ? WHERE LOWER(customer_email) = LOWER(?)", (customer_id, clean_email))
    
    conn.commit()
    conn.close()
    
    return {
        "id": customer_id,
        "email": clean_email,
        "full_name": full_name.strip(),
        "phone": phone or "",
        "address_line1": address_line1 or "",
        "address_line2": address_line2 or "",
        "city": city or "",
        "state": state or "",
        "postal_code": postal_code or "",
        "country": country or "United States"
    }


def authenticate_customer(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticates email and password. Returns customer data on success."""
    customer = get_customer_by_email(email)
    if not customer:
        return None
    if not verify_password(password, customer["password_hash"]):
        return None
        
    return {
        "id": customer["id"],
        "email": customer["email"],
        "full_name": customer["full_name"],
        "phone": customer["phone"] or "",
        "address_line1": customer["address_line1"] or "",
        "address_line2": customer["address_line2"] or "",
        "city": customer["city"] or "",
        "state": customer["state"] or "",
        "postal_code": customer["postal_code"] or "",
        "country": customer["country"] or "United States"
    }


def update_customer_profile(customer_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Updates customer's profile and shipping address."""
    allowed_fields = [
        "full_name", "phone", "address_line1", "address_line2",
        "city", "state", "postal_code", "country"
    ]
    set_clauses = []
    values = []
    for field in allowed_fields:
        if field in updates:
            set_clauses.append(f"{field} = ?")
            values.append(updates[field])
            
    if not set_clauses:
        return get_customer_by_id(customer_id) or {}
        
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    values.append(customer_id)
    
    query = f"UPDATE customers SET {', '.join(set_clauses)} WHERE id = ?"
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(query, values)
    conn.commit()
    conn.close()
    
    cust = get_customer_by_id(customer_id)
    if cust:
        cust.pop("password_hash", None)
    return cust or {}


def get_customer_orders(customer_id: str, email: str) -> List[Dict[str, Any]]:
    """Fetches all orders placed by this customer (matched by ID or email)."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM orders
        WHERE customer_id = ? OR LOWER(customer_email) = LOWER(?)
        ORDER BY created_at DESC
    """, (customer_id, email.strip().lower()))
    order_rows = [dict(r) for r in c.fetchall()]
    
    orders = []
    for order in order_rows:
        oid = order["order_id"]
        c.execute("SELECT * FROM order_items WHERE order_id = ?", (oid,))
        items = [dict(it) for it in c.fetchall()]
        order["items"] = items
        orders.append(order)
        
    conn.close()
    return orders
