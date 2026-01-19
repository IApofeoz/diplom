from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

import models, schemas
from database import engine, get_db

# Секретный ключ для подписи токенов (в реальном проекте хранить в .env!)
SECRET_KEY = "super-secret-key-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30*7*2

# Схема авторизации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Создаем таблицы автоматически (в проде лучше использовать Alembic)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- БЕЗОПАСНОСТЬ (ХЕШИРОВАНИЕ) ---
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# --- ЭНДПОИНТЫ ---

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. Проверяем, есть ли такой email
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Проверяем username
    db_user_name = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user_name:
        raise HTTPException(status_code=400, detail="Username already taken")

    # 3. Хешируем пароль
    hashed_pw = get_password_hash(user.password)


    # 4. Создаем пользователя
    new_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_pw
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/login", response_model=Token)
def login(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. Ищем пользователя по email
    # (Обратите внимание: мы используем UserCreate, но нам нужны только email и password)
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # 2. Проверяем пароль
    if not pwd_context.verify(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # 3. Генерируем токен
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}
