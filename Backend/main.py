import os
import secrets
import shutil
import uuid
from datetime import datetime, timedelta

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

# Локальные модули
import models
import schemas
from database import engine, get_db

# --- КОНФИГУРАЦИЯ ---
SECRET_KEY = "super-secret-key-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 7 

os.makedirs("static/uploads", exist_ok=True)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto", argon2__type="id")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        was_offline = user_id not in self.active_connections
        if was_offline:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        if was_offline:
            await self.broadcast_status(user_id, "online")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                return True 
        return False

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except RuntimeError:
                    pass
    
    async def broadcast_status(self, user_id: int, status: str):
        message = {"type": "status_update", "user_id": user_id, "status": status}
        for uid, sockets in list(self.active_connections.items()):
            for ws in sockets:
                try:
                    await ws.send_json(message)
                except RuntimeError:
                    pass

manager = ConnectionManager()

class Token(BaseModel):
    access_token: str
    token_type: str

# --- ЭНДПОИНТЫ ---

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"static/uploads/{unique_filename}"
    
    with open(file_path, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    return {"url": f"http://localhost:8000/{file_path}"}

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed_pw = get_password_hash(user.password)
    new_user = models.User(email=user.email, username=user.username, hashed_password=hashed_pw)
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

@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.put("/users/me", response_model=schemas.UserOut)
def update_user_me(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if user_update.username is not None:
        new_username = user_update.username.strip()
        if new_username != current_user.username:
            existing = db.query(models.User).filter(models.User.username == new_username).first()
            if existing:
                raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
            current_user.username = new_username

    if user_update.phone_number is not None:
        current_user.phone_number = user_update.phone_number
        
    if user_update.birth_date is not None:
        current_user.birth_date = user_update.birth_date
    
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
        
    db.commit()
    db.refresh(current_user)
    return current_user

@app.get("/users", response_model=list[schemas.UserWithLastMessage])
def get_users_with_last_message(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    users = db.query(models.User).filter(models.User.id != current_user.id).all()
    result = []
    for user in users:
        last_msg = db.query(models.Message).filter(
            or_(
                (models.Message.sender_id == current_user.id) & (models.Message.recipient_id == user.id),
                (models.Message.sender_id == user.id) & (models.Message.recipient_id == current_user.id)
            )
        ).order_by(models.Message.timestamp.desc()).first()

        result.append({
            "id": user.id,
            "username": user.username,
            "last_message": last_msg.content if last_msg else "Начните общение",
            "last_message_time": last_msg.timestamp.isoformat() if last_msg else None,
            "is_online": user.id in manager.active_connections,
            "avatar_url": user.avatar_url,
            "phone_number": user.phone_number,
            "birth_date": user.birth_date
        })
    return result

@app.get("/messages/{user_id}", response_model=list[schemas.MessageOut])
def get_messages(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    messages = db.query(models.Message).filter(
        or_(
            and_(models.Message.sender_id == current_user.id, models.Message.recipient_id == user_id),
            and_(models.Message.sender_id == user_id, models.Message.recipient_id == current_user.id)
        )
    ).order_by(models.Message.timestamp.asc()).all()

    # Формируем ответ вручную, чтобы заполнить данные о цитате
    result = []
    for msg in messages:
        reply_data = None
        if msg.reply_to:
            # Находим автора того сообщения, на которое ответили
            sender = db.query(models.User).filter(models.User.id == msg.reply_to.sender_id).first()
            reply_data = {
                "id": msg.reply_to.id,
                "content": msg.reply_to.content,
                "sender_username": sender.username if sender else "Unknown"
            }
            
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "recipient_id": msg.recipient_id,
            "content": msg.content,
            "timestamp": msg.timestamp,
            "is_read": msg.is_read,
            "is_encrypted": msg.is_encrypted,
            "reply_to": reply_data
        })
        
    return result

@app.get("/users/search", response_model=list[schemas.UserOut])
def search_users(q: str = Query(..., min_length=1), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Ищем пользователей по username или email (регистронезависимо через ilike)
    # Используем current_user.id != models.User.id, чтобы не находить самого себя
    users = db.query(models.User).filter(
        and_(
            models.User.id != current_user.id,
            or_(
                models.User.username.ilike(f"%{q}%"), # ilike - case insensitive search в Postgres
                models.User.email.ilike(f"%{q}%")
            )
        )
    ).all()
    
    return users

@app.get("/messages/{contact_id}/search", response_model=list[schemas.MessageOut])
def search_messages(
    contact_id: int, 
    q: str = Query(..., min_length=1), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # Ищем сообщения только между мной и контактом, содержащие текст запроса
    messages = db.query(models.Message).filter(
        and_(
            models.Message.content.ilike(f"%{q}%"), # Поиск подстроки
            or_(
                and_(models.Message.sender_id == current_user.id, models.Message.recipient_id == contact_id),
                and_(models.Message.sender_id == contact_id, models.Message.recipient_id == current_user.id)
            )
        )
    ).order_by(models.Message.timestamp.desc()).all() # Сначала новые

    # Формируем ответ вручную для цитат (та же логика, что в get_messages)
    result = []
    for msg in messages:
        reply_data = None
        if msg.reply_to_id and msg.reply_to:
             sender = db.query(models.User).filter(models.User.id == msg.reply_to.sender_id).first()
             reply_data = {
                 "id": msg.reply_to.id,
                 "content": msg.reply_to.content,
                 "sender_username": sender.username if sender else "Unknown"
             }
        
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "recipient_id": msg.recipient_id,
            "content": msg.content,
            "timestamp": msg.timestamp,
            "is_read": msg.is_read,
            "is_encrypted": msg.is_encrypted,
            "reply_to": reply_data
        })
        
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
    # 1. Аутентификация
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

    # 2. Подключение
    await manager.connect(websocket, user.id)
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            # --- ЛОГИКА: СТАТУС ПЕЧАТИ ---
            if msg_type == "typing":
                recipient_id = data.get("recipient_id")
                await manager.send_personal_message(
                    {"type": "user_typing", "sender_id": user.id}, 
                    recipient_id
                )
                continue

            # --- ЛОГИКА: ПРОЧИТАНО ---
            elif msg_type == "read_messages":
                sender_id = data.get("sender_id")
                db.query(models.Message).filter(models.Message.sender_id == sender_id, models.Message.recipient_id == user.id, models.Message.is_read == False).update({"is_read": True})
                db.commit()
                await manager.send_personal_message({"type": "messages_read", "user_id": user.id}, sender_id)
                continue

            # --- ЛОГИКА: УДАЛЕНИЕ ---
            elif msg_type == "delete_message":
                msg_id = data.get("message_id")
                msg_to_delete = db.query(models.Message).filter(models.Message.id == msg_id).first()
                if msg_to_delete and msg_to_delete.sender_id == user.id:
                    recipient_id = msg_to_delete.recipient_id
                    db.delete(msg_to_delete)
                    db.commit()
                    update_payload = {"type": "message_deleted", "id": msg_id}
                    await manager.send_personal_message(update_payload, user.id)
                    await manager.send_personal_message(update_payload, recipient_id)
                continue

            # --- ЛОГИКА: РЕДАКТИРОВАНИЕ ---
            elif msg_type == "edit_message":
                msg_id = data.get("message_id")
                new_content = data.get("new_content")
                msg_to_edit = db.query(models.Message).filter(models.Message.id == msg_id).first()
                if msg_to_edit and msg_to_edit.sender_id == user.id and new_content:
                    msg_to_edit.content = new_content
                    db.commit()
                    update_payload = {"type": "message_edited", "id": msg_id, "content": new_content}
                    await manager.send_personal_message(update_payload, user.id)
                    await manager.send_personal_message(update_payload, msg_to_edit.recipient_id)
                continue

            # --- ЛОГИКА: ОБЫЧНОЕ СООБЩЕНИЕ (С ОТВЕТОМ) ---
            recipient_id = data.get("recipient_id")
            content = data.get("content")
            reply_to_id = data.get("reply_to_id") # <--- Получаем ID ответа
            
            if recipient_id and content:
                new_msg = models.Message(
                    sender_id=user.id, 
                    recipient_id=recipient_id, 
                    content=content, 
                    is_read=False, 
                    is_encrypted=False,
                    reply_to_id=reply_to_id # <--- Сохраняем связь в БД
                )
                db.add(new_msg)
                db.commit()
                db.refresh(new_msg)
                
                # Подготовка данных о цитате (чтобы фронтенд мог её сразу отрисовать)
                reply_data = None
                if reply_to_id:
                     replied_msg = db.query(models.Message).filter(models.Message.id == reply_to_id).first()
                     if replied_msg:
                         reply_sender = db.query(models.User).filter(models.User.id == replied_msg.sender_id).first()
                         reply_data = {
                             "id": replied_msg.id,
                             "content": replied_msg.content,
                             "sender_username": reply_sender.username if reply_sender else "Unknown"
                         }

                msg_response = {
                    "type": "new_message",
                    "id": new_msg.id,
                    "sender_id": user.id,
                    "recipient_id": recipient_id,
                    "content": content,
                    "timestamp": new_msg.timestamp.isoformat(),
                    "is_read": False,
                    "is_encrypted": False,
                    "reply_to": reply_data # <--- Отправляем объект цитаты клиенту
                }
                
                await manager.send_personal_message(msg_response, recipient_id)
                await manager.send_personal_message(msg_response, user.id)

    except WebSocketDisconnect:
        is_offline = manager.disconnect(websocket, user.id)
        if is_offline:
            await manager.broadcast_status(user.id, "offline")
