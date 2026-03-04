"""
security.py — Basic Auth + bcrypt + ролі
"""
import secrets
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.database import get_conn

security = HTTPBasic()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_user(username: str, password: str, role: str = "operator"):
    """Викликати один раз для створення користувачів."""
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                (username, hash_password(password), role),
            )
            print(f"[AUTH] Користувач '{username}' ({role}) створений")
        except Exception as e:
            print(f"[AUTH] Помилка: {e}")


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=?", (credentials.username,)
        ).fetchone()
    if not row or not verify_password(credentials.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний логін або пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {"username": row["username"], "role": row["role"]}


def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Потрібні права адміністратора")
    return user
