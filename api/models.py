from api.database import Base
from datetime import datetime, timezone
from typing import List
from sqlalchemy import Column, ForeignKey, Integer, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TIMESTAMP

association_table = Table(
    "association_table",
    Base.metadata,
    Column("subscriber_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("following_id", Integer, ForeignKey("users.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    api_key: Mapped[str] = mapped_column(unique=True, nullable=False)

    # Пользователи, которые подписаны на данного пользователя
    subscribers = relationship(
        "User",
        secondary="association_table",
        primaryjoin="User.id==association_table.c.following_id",
        secondaryjoin="User.id==association_table.c.subscriber_id",
        back_populates="following",
        lazy="selectin"
    )

    # Пользователи, которых читает данный пользователь
    following = relationship(
        "User",
        secondary="association_table",
        primaryjoin="User.id==association_table.c.subscriber_id",
        secondaryjoin="User.id==association_table.c.following_id",
        back_populates="subscribers",
        lazy="selectin"
        )

    tweets: Mapped[List["Tweet"]] = relationship(
        back_populates="author", cascade="all, delete-orphan", lazy="selectin"
    )

    likes: Mapped[List["Like"]] = relationship(back_populates="user", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"User {self.name}"


class Tweet(Base):
    __tablename__ = "tweets"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc), type_=TIMESTAMP(timezone=True))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    author: Mapped["User"] = relationship(back_populates="tweets", lazy="selectin")
    likes: Mapped[List["Like"]] = relationship(back_populates="tweet", cascade="all, delete-orphan", lazy="selectin")
    image: Mapped[List["Image"]] = relationship(back_populates="tweet", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Tweet {self.content[:50]}>"


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweets.id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="likes", lazy="selectin")
    tweet: Mapped["Tweet"] = relationship(back_populates="likes", lazy="selectin")

    def __repr__(self):
        return f'User {self.user.name} liked tweet "{self.tweet.content[:50]}"'


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(nullable=False)
    tweet_id: Mapped[int] = mapped_column(ForeignKey("tweets.id"), nullable=True)

    tweet: Mapped["Tweet"] = relationship(back_populates="image", lazy="selectin")

    def __repr__(self):
        return f"Image <{self.url}>"
