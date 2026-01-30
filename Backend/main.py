from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from fastapi.staticfiles import StaticFiles
from fastapi import UploadFile, File        

import secrets
import models, schemas
from database import engine, get_db

# --- КОНФИГУРАЦИЯ ---
SECRET_KEY = "super-secret-key-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 7  # 1 неделя

# Создаем таблицы (в продакшене лучше использовать Alembic)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- БЕЗОПАСНОСТЬ ---
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__type="id"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Зависимость для получения текущего пользователя
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        # Храним: user_id -> [WebSocket1, WebSocket2] (поддержка нескольких вкладок)
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        
        # Проверяем, был ли юзер онлайн ДО этого подключения
        was_offline = user_id not in self.active_connections
        
        if was_offline:
            self.active_connections[user_id] = []
            
        self.active_connections[user_id].append(websocket)
        
        # Если юзер только что появился в сети — оповещаем всех
        if was_offline:
            await self.broadcast_status(user_id, "online")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Возвращает True, если пользователь полностью отключился (стал оффлайн)"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # Если у пользователя больше нет активных соединений
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                return True # Стал оффлайн
        return False

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            # Отправляем во все открытые вкладки пользователя
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except RuntimeError:
                    pass
    
    async def broadcast_status(self, user_id: int, status: str):
        """Рассылает всем подключенным пользователям уведомление о смене статуса"""
        message = {
            "type": "status_update",
            "user_id": user_id,
            "status": status
        }
        # Итерируемся по копии ключей, чтобы избежать ошибки изменения словаря во время итерации
        for uid, sockets in list(self.active_connections.items()):
            for ws in sockets:
                try:
                    await ws.send_json(message)
                except RuntimeError:
                    pass

manager = ConnectionManager()


# --- МОДЕЛИ ОТВЕТОВ (Pydantic) для токена ---
class Token(BaseModel):
    access_token: str
    token_type: str

# --- ЭНДПОИНТЫ: AUTH ---

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed_pw = get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_pw
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=Token)
def login(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or not pwd_context.verify(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/forgot-password")
def forgot_password(payload: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return {"message": "Instruction sent if email exists"}

    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(minutes=15)

    user.reset_token = token
    user.reset_token_expires = expires
    db.commit()

    reset_link = f"http://localhost:5173/reset-password?token={token}"
    print(f"\n📧 RESET LINK: {reset_link}\n")
    return {"message": "Reset link sent (check console)"}

@app.post("/reset-password")
def reset_password(payload: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.reset_token == payload.token).first()
    if not user or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.hashed_password = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"message": "Password updated"}

# --- ЭНДПОИНТЫ: ЧАТ И ПОЛЬЗОВАТЕЛИ ---

@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# main.py

@app.put("/users/me", response_model=schemas.UserOut)
def update_user_me(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Смена юзернейма
    if user_update.username is not None:
        # Убираем пробелы (на всякий случай)
        new_username = user_update.username.strip()
        
        # Если имя реально отличается от текущего
        if new_username != current_user.username:
            # Проверяем занятость
            existing_user = db.query(models.User).filter(models.User.username == new_username).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
            
            current_user.username = new_username

    # 2. Телефон
    if user_update.phone_number is not None:
        if current_user.phone_number != user_update.phone_number:
            current_user.phone_number = user_update.phone_number
        
    # 3. Дата рождения
    if user_update.birth_date is not None:
        if current_user.birth_date != user_update.birth_date:
            current_user.birth_date = user_update.birth_date
        
    db.commit()
    db.refresh(current_user)
    return current_user


@app.get("/users", response_model=list[schemas.UserWithLastMessage])
def get_users_with_last_message(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # 1. Получаем всех пользователей (кроме себя)
    users = db.query(models.User).filter(models.User.id != current_user.id).all()
    
    result = []
    for user in users:
        # 2. Ищем ПОСЛЕДНЕЕ сообщение
        last_msg = db.query(models.Message).filter(
            or_(
                (models.Message.sender_id == current_user.id) & (models.Message.recipient_id == user.id),
                (models.Message.sender_id == user.id) & (models.Message.recipient_id == current_user.id)
            )
        ).order_by(models.Message.timestamp.desc()).first()

        # 3. Формируем ответ, проверяя статус онлайн через manager
        result.append({
            "id": user.id,
            "username": user.username,
            "last_message": last_msg.content if last_msg else "Начните общение",
            "last_message_time": last_msg.timestamp.isoformat() if last_msg else None,
            
            # НОВОЕ ПОЛЕ: true, если id пользователя есть в списке активных подключений
            "is_online": user.id in manager.active_connections 
        })
        
    return result


@app.get("/messages/{contact_id}", response_model=list[schemas.MessageOut])
def get_history(
    contact_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Возвращает историю переписки между текущим пользователем и contact_id"""
    messages = db.query(models.Message).filter(
        or_(
            (models.Message.sender_id == current_user.id) & (models.Message.recipient_id == contact_id),
            (models.Message.sender_id == contact_id) & (models.Message.recipient_id == current_user.id)
        )
    ).order_by(models.Message.timestamp.asc()).all()
    
    return messages

# --- WEBSOCKET ENDPOINT ---
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(...), 
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint. 
    Токен передается через query-параметр: ws://host/ws?token=...
    """
    # 1. Валидация пользователя при подключении
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Подключение (автоматически отправит "online", если юзер только зашел)
    await manager.connect(websocket, user.id)
    
    try:
        while True:
            # 3. Получение сообщения от клиента
            data = await websocket.receive_json()
            
            # --- ЛОГИКА ПРОЧТЕНИЯ ---
            if data.get("type") == "read_messages":
                sender_id = data.get("sender_id")
                
                # Помечаем все сообщения ОТ sender_id ДЛЯ user.id как прочитанные
                db.query(models.Message).filter(
                    models.Message.sender_id == sender_id,
                    models.Message.recipient_id == user.id,
                    models.Message.is_read == False
                ).update({"is_read": True})
                db.commit()
                
                # Уведомляем отправителя (sender_id), что его сообщения прочитаны
                await manager.send_personal_message({
                    "type": "messages_read",
                    "user_id": user.id  # Кто прочитал (Я)
                }, sender_id)
                continue

            # --- ЛОГИКА ОТПРАВКИ СООБЩЕНИЯ ---
            # Ожидаемый формат: {"recipient_id": 2, "content": "Привет"}
            recipient_id = data.get("recipient_id")
            content = data.get("content")
            
            if not recipient_id or not content:
                continue

            # 4. Сохранение в БД
            new_msg = models.Message(
                sender_id=user.id,
                recipient_id=recipient_id,
                content=content,
                is_read=False,
                is_encrypted=False 
            )
            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)

            # 5. Подготовка ответа (JSON)
            msg_response = {
                "type": "new_message",
                "id": new_msg.id,
                "sender_id": user.id,
                "recipient_id": recipient_id,
                "content": content,
                "timestamp": new_msg.timestamp.isoformat(), 
                "is_read": False,
                "is_encrypted": False
            }

            # 6. Рассылка получателю и себе (для синхронизации)
            await manager.send_personal_message(msg_response, recipient_id)
            await manager.send_personal_message(msg_response, user.id)

    except WebSocketDisconnect:
        # При отключении проверяем, стал ли юзер полностью оффлайн
        is_offline = manager.disconnect(websocket, user.id)
        if is_offline:
            await manager.broadcast_status(user.id, "offline")
