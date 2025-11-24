"""Database models for the relic application."""
from sqlalchemy import Column, String, Integer, DateTime, LargeBinary, ForeignKey, Boolean, JSON, Text, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid


Base = declarative_base()


# Association table for many-to-many relationship between relics and tags
relic_tags = Table(
    'relic_tags',
    Base.metadata,
    Column('relic_id', String, ForeignKey('relic.id')),
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

    relics = relationship("Relic", back_populates="user")


class Relic(Base):
    """
    Relic model.

    ID format: 32-character hexadecimal (GitHub Gist-style)
    Example: f47ac10b58cc4372a5670e02b2c3d479
    Generated via secrets.token_hex(16) for 128 bits of entropy
    """
    __tablename__ = "relic"

    id = Column(String(32), primary_key=True)  # 32-char hex IDs
    user_id = Column(String, ForeignKey('user.id'), nullable=True)

    # Content metadata
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    content_type = Column(String, default="text/plain")
    language_hint = Column(String, nullable=True)
    size_bytes = Column(Integer)

    # Version tracking
    parent_id = Column(String, ForeignKey('relic.id'), nullable=True)
    root_id = Column(String, nullable=True, index=True)
    version_number = Column(Integer, default=1)
    fork_of = Column(String, nullable=True)

    # Storage
    s3_key = Column(String)

    # Access control
    # public: Listed in recents, discoverable
    # private: Not listed, only accessible via direct URL (which serves as the access token)
    access_level = Column(String, default="public")
    password_hash = Column(String, nullable=True)

    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)

    # Processing metadata (stored as JSON for flexibility)
    processing_metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="relics")
    parent = relationship("Relic", remote_side=[id], backref="children", foreign_keys=[parent_id])
    tags = relationship("Tag", secondary=relic_tags, back_populates="relics")

class Tag(Base):
    """Tag model."""
    __tablename__ = "tag"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    relics = relationship("Relic", secondary=relic_tags, back_populates="tags")