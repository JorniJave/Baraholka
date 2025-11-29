from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship
import datetime

Base = declarative_base()
engine = create_async_engine("sqlite+aiosqlite:///baraholka.db")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String)
    privilege = Column(String, default="user")
    posts_count = Column(Integer, default=0)
    referrals_count = Column(Integer, default=0)
    referrer_id = Column(Integer, nullable=True)  # ID пользователя, который пригласил
    last_post_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.now)
    banned = Column(Boolean, default=False)  # ✅ ДОБАВЛЯЕМ ПОЛЕ БАНА

    # Связи
    posts = relationship("Post", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")
    referrals = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")

    def __init__(self, id=None, username=None, privilege="user", posts_count=0,
                 referrals_count=0, referrer_id=None, last_post_time=None, created_at=None, banned=False):
        self.id = id
        self.username = username
        self.privilege = privilege
        self.posts_count = posts_count
        self.referrals_count = referrals_count
        self.referrer_id = referrer_id
        self.last_post_time = last_post_time
        self.created_at = created_at or datetime.datetime.now()
        self.banned = banned  # ✅ ДОБАВЛЯЕМ В КОНСТРУКТОР


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey("users.id"))
    referred_id = Column(Integer, unique=True)  # ID приглашенного пользователя
    created_at = Column(DateTime, default=datetime.datetime.now)

    # Связи
    referrer = relationship("User", back_populates="referrals")

    def __init__(self, referrer_id=None, referred_id=None, created_at=None):
        self.referrer_id = referrer_id
        self.referred_id = referred_id
        self.created_at = created_at or datetime.datetime.now()


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    photo_id = Column(String)
    title = Column(String)
    price = Column(String)  # цена/торг
    description = Column(Text)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.datetime.now)

    # Связи
    user = relationship("User", back_populates="posts")

    def __init__(self, user_id=None, photo_id=None, title=None, price=None,
                 description=None, status="active", created_at=None):
        self.user_id = user_id
        self.photo_id = photo_id
        self.title = title
        self.price = price
        self.description = description
        self.status = status
        self.created_at = created_at or datetime.datetime.now()


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    theme = Column(String)  # тема тикета согласно разделу 3 ТЗ
    status = Column(String, default="new")  # new/in_progress/closed
    admin_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    # Связи
    user = relationship("User", back_populates="tickets")
    messages = relationship("TicketMessage", back_populates="ticket")

    def __init__(self, user_id=None, theme=None, status="new", admin_id=None, created_at=None):
        self.user_id = user_id
        self.theme = theme
        self.status = status
        self.admin_id = admin_id
        self.created_at = created_at or datetime.datetime.now()


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    user_id = Column(Integer)
    message_text = Column(Text)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

    # Связи
    ticket = relationship("Ticket", back_populates="messages")

    def __init__(self, ticket_id=None, user_id=None, message_text=None,
                 is_admin=False, created_at=None):
        self.ticket_id = ticket_id
        self.user_id = user_id
        self.message_text = message_text
        self.is_admin = is_admin
        self.created_at = created_at or datetime.datetime.now()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)