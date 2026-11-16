from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey
from sqlalchemy import Integer, SmallInteger, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "roles"
    role_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    role_name: Mapped[str] = mapped_column(String(40), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.role_id"))


class Category(Base):
    __tablename__ = "categories"
    category_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Source(Base):
    __tablename__ = "sources"
    source_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    source_type: Mapped[str] = mapped_column(String(40))
    url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)


class Audience(Base):
    __tablename__ = "audiences"
    audience_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Event(Base):
    __tablename__ = "events"
    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="planned")
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"))
    __table_args__ = (CheckConstraint("status IN ('planned','ongoing','completed','cancelled')"),)


class Media(Base):
    __tablename__ = "media"
    media_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(String(10))
    file_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.event_id"))
    __table_args__ = (CheckConstraint("media_type IN ('image','video')"),)


class Announcement(Base):
    __tablename__ = "announcements"
    announcement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"))
    audience_id: Mapped[int] = mapped_column(ForeignKey("audiences.audience_id"))
    __table_args__ = (CheckConstraint("end_date >= start_date"),)


class Playlist(Base):
    __tablename__ = "playlists"
    playlist_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.playlist_id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    display_duration: Mapped[int] = mapped_column(Integer)
    media_id: Mapped[int | None] = mapped_column(ForeignKey("media.media_id"))
    announcement_id: Mapped[int | None] = mapped_column(ForeignKey("announcements.announcement_id"))
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.event_id"))
    __table_args__ = (UniqueConstraint("playlist_id", "position"),)


class Display(Base):
    __tablename__ = "displays"
    display_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    location: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Schedule(Base):
    __tablename__ = "schedules"
    schedule_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.playlist_id"))
    display_id: Mapped[int] = mapped_column(ForeignKey("displays.display_id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


MODELS = {
    "roles": Role,
    "users": User,
    "categories": Category,
    "sources": Source,
    "audiences": Audience,
    "events": Event,
    "media": Media,
    "announcements": Announcement,
    "playlists": Playlist,
    "playlist_items": PlaylistItem,
    "displays": Display,
    "schedules": Schedule,
}
