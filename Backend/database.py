from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Строка подключения: postgresql://USER:PASSWORD@HOST/DB_NAME
# Замените 'postgres', 'password' и 'messenger_db' на свои данные
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Vfnhbwf_2104_2107@localhost/messenger_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Функция для получения сессии БД (dependency)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
