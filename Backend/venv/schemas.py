from pydantic import BaseModel, EmailStr
from datetime import datetime, date

# --- USERS ---

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: str | None = None
    phone_number: str | None = None
    birth_date: date | None = None

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    avatar_url: str | None = None
    phone_number: str | None = None
    birth_date: date | None = None

    class Config:
        from_attributes = True # В Pydantic v2 это заменило orm_mode = True
        # Если у вас старый Pydantic v1, оставьте orm_mode = True

class UserWithLastMessage(BaseModel):
    id: int
    username: str
    last_message: str | None = None
    last_message_time: str | None = None
    is_online: bool = False
    avatar_url: str | None = None
    phone_number: str | None = None
    birth_date: date | None = None

# --- AUTH ---

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# --- MESSAGES ---

class MessageCreate(BaseModel):
    recipient_id: int
    content: str
    is_encrypted: bool = False

class MessageOut(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    content: str
    is_encrypted: bool
    timestamp: datetime
    is_read: bool

    class Config:
        from_attributes = True # Или orm_mode = True для Pydantic v1
