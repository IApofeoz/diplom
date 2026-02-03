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
    avatar_url: str | None = None

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    avatar_url: str | None = None
    phone_number: str | None = None
    birth_date: date | None = None

    class Config:
        from_attributes = True

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

# 1. Схема для вложенного сообщения (на которое ответили)
class MessageReply(BaseModel):
    id: int
    content: str
    sender_username: str  # Имя того, кого цитируем

    class Config:
        from_attributes = True

# 2. Обновленная схема создания (добавили reply_to_id)
class MessageCreate(BaseModel):
    recipient_id: int
    content: str
    is_encrypted: bool = False
    reply_to_id: int | None = None 

# 3. Обновленная схема отображения (добавили reply_to)
class MessageOut(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    content: str
    is_encrypted: bool
    timestamp: datetime
    is_read: bool
    
    reply_to: MessageReply | None = None # Вложенный объект

    class Config:
        from_attributes = True
