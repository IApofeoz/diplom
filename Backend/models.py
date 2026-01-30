from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text, Boolean 
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, nullable=True) # Храним как строку "+7900..."
    birth_date = Column(Date, nullable=True)     # Только дата, без времени
    avatar_url = Column(String, nullable=True)
    hashed_password = Column(String)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Публичный ключ для будущего E2E шифрования
    public_key = Column(String, nullable=True)

    # Связи, чтобы ORM знала о сообщениях
    # Используем кавычки "Message", чтобы избежать ошибки, если класс еще не объявлен
    sent_messages = relationship("Message", foreign_keys="[Message.sender_id]", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="[Message.recipient_id]", back_populates="recipient")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    
    # Внешние ключи на таблицу users
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Текст сообщения
    content = Column(Text, nullable=False)

    # Флаг шифрования (на будущее)
    is_encrypted = Column(Boolean, default=False)

    is_read = Column(Boolean, default=False)
    
    # Время отправки
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Связи с пользователями
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")
