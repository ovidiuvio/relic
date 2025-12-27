"""Database models for the relic application."""
from sqlalchemy import Column, String, Integer, DateTime, LargeBinary, ForeignKey, Boolean, JSON, Text, Table, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
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




class Relic(Base):
    """
    Relic model.

    ID format: 32-character hexadecimal (GitHub Gist-style)
    Example: f47ac10b58cc4372a5670e02b2c3d479
    Generated via secrets.token_hex(16) for 128 bits of entropy
    """
    __tablename__ = "relic"

    id = Column(String(32), primary_key=True)  # 32-char hex IDs
    client_id = Column(String, ForeignKey('client_key.id'), nullable=True, index=True)

    # Content metadata
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    content_type = Column(String, default="text/plain")
    language_hint = Column(String, nullable=True)
    size_bytes = Column(Integer)

    # Fork tracking (but no versioning)
    fork_of = Column(String, nullable=True, index=True)  # Which relic this was forked from

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
    access_count = Column(Integer, default=0)
    bookmark_count = Column(Integer, default=0)

    # Relationships
    tags = relationship("Tag", secondary=relic_tags, back_populates="relics")

class ClientKey(Base):
    """Client identification key."""
    __tablename__ = "client_key"

    id = Column(String(32), primary_key=True)  # 32-char hex client ID
    name = Column(String, nullable=True)  # User's display name
    created_at = Column(DateTime, default=datetime.utcnow)
    relic_count = Column(Integer, default=0)

    # Relationships
    relics = relationship("Relic", backref="owner_client")


class Tag(Base):
    """Tag model."""
    __tablename__ = "tag"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    relics = relationship("Relic", secondary=relic_tags, back_populates="tags")


class ClientBookmark(Base):
    """Client bookmark model - tracks which relics a client has bookmarked."""
    __tablename__ = "client_bookmark"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(32), ForeignKey('client_key.id'), nullable=False, index=True)
    relic_id = Column(String(32), ForeignKey('relic.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    client = relationship("ClientKey", backref="bookmarks")
    relic = relationship("Relic", backref="bookmarked_by")

    # Unique constraint to prevent duplicate bookmarks
    __table_args__ = (
        UniqueConstraint('client_id', 'relic_id', name='unique_client_relic_bookmark'),
    )


class RelicReport(Base):
    """Report model for flagging inappropriate relics."""
    __tablename__ = "relic_report"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    relic_id = Column(String(32), ForeignKey('relic.id'), nullable=False, index=True)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Optional: track reporter if authenticated (not strictly required by spec but good practice)
    # reporter_id = Column(String, ForeignKey('client_key.id'), nullable=True)

        # Relationships
    relic = relationship("Relic", backref="reports")


class Comment(Base):
    """Comment model for line-specific comments on relics."""
    __tablename__ = "comment"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    relic_id = Column(String(32), ForeignKey('relic.id'), nullable=False, index=True)
    client_id = Column(String(32), ForeignKey('client_key.id'), nullable=True)
    line_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    parent_id = Column(String, ForeignKey('comment.id'), nullable=True)

    # Relationships
    relic = relationship("Relic", backref="comments")
    client = relationship("ClientKey", backref="comments")
    replies = relationship("Comment", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan")
