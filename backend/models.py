"""Database models for the paste application."""
from sqlalchemy import Column, String, Integer, DateTime, LargeBinary, ForeignKey, Boolean, JSON, Text, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid


Base = declarative_base()


# Association table for many-to-many relationship between pastes and tags
paste_tags = Table(
    'paste_tags',
    Base.metadata,
    Column('paste_id', String, ForeignKey('paste.id')),
    Column('tag_id', String, ForeignKey('tag.id'))
)


class User(Base):
    """User model."""
    __tablename__ = "user"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    pastes = relationship("Paste", back_populates="user")


class Paste(Base):
    """Paste model."""
    __tablename__ = "paste"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    user_id = Column(String, ForeignKey('user.id'), nullable=True)

    # Content metadata
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    content_type = Column(String, default="text/plain")
    language_hint = Column(String, nullable=True)
    size_bytes = Column(Integer)

    # Version tracking
    parent_id = Column(String, ForeignKey('paste.id'), nullable=True)
    root_id = Column(String, nullable=True, index=True)
    version_number = Column(Integer, default=1)
    fork_of = Column(String, nullable=True)

    # Storage
    s3_key = Column(String)

    # Access control
    access_level = Column(String, default="public")  # public, unlisted, private
    password_hash = Column(String, nullable=True)

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)

    # Processing metadata (stored as JSON for flexibility)
    metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="pastes")
    parent = relationship("Paste", remote_side=[id], backref="children", foreign_keys=[parent_id])
    tags = relationship("Tag", secondary=paste_tags, back_populates="pastes")


class Tag(Base):
    """Tag model."""
    __tablename__ = "tag"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pastes = relationship("Paste", secondary=paste_tags, back_populates="tags")
