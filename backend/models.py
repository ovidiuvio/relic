"""Database models for the relic application."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Text, Table, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from datetime import datetime
import uuid
from typing import Optional


Base = declarative_base()


# Association table for many-to-many relationship between relics and tags
relic_tags = Table(
    'relic_tags',
    Base.metadata,
    Column('relic_id', String, ForeignKey('relic.id', ondelete="CASCADE")),
    Column('tag_id', String, ForeignKey('tag.id', ondelete="CASCADE"))
)


# Association table for many-to-many relationship between spaces and relics
space_relics = Table(
    'space_relics',
    Base.metadata,
    Column('space_id', String(32), ForeignKey('space.id', ondelete="CASCADE"), primary_key=True),
    Column('relic_id', String(32), ForeignKey('relic.id', ondelete="CASCADE"), primary_key=True)
)


class Space(Base):
    """
    Space model.

    Groups relics together. Can be public or private.
    Private spaces have an access list.
    """
    __tablename__ = "space"

    id = Column(String(32), primary_key=True)  # 32-char hex ID
    name = Column(String, nullable=False)
    owner_id = Column(String(32), ForeignKey('users.id'), nullable=False, index=True)
    visibility = Column(String, default="public")  # "public" or "private"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    owner = relationship("User", backref="owned_spaces", foreign_keys=[owner_id], lazy="raise")
    relics = relationship("Relic", secondary=space_relics, back_populates="spaces", lazy="raise")
    access_list = relationship("SpaceAccess", back_populates="space", cascade="all, delete-orphan", lazy="raise")


class SpaceAccess(Base):
    """
    Space access list model.
    Tracks which users have access to a private space, and their roles.
    """
    __tablename__ = "space_access"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    space_id = Column(String(32), ForeignKey('space.id', ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(32), ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, default="viewer")  # "viewer" or "editor"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    space = relationship("Space", back_populates="access_list", lazy="raise")
    user = relationship("User", backref="space_accesses", lazy="raise")

    # Unique constraint to prevent duplicate access entries
    __table_args__ = (
        UniqueConstraint('space_id', 'user_id', name='unique_space_user_access'),
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
    user_id = Column(String, ForeignKey('users.id'), nullable=True, index=True)

    # Content metadata
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    content_type = Column(String, default="text/plain")
    language_hint = Column(String, nullable=True)
    # BigInteger: int4 caps at ~2.1 GB, uploads can be far larger
    size_bytes = Column(BigInteger)

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
    tags = relationship("Tag", secondary=relic_tags, back_populates="relics", lazy="raise")
    spaces = relationship("Space", secondary=space_relics, back_populates="relics", lazy="raise")
    access_list = relationship("RelicAccess", back_populates="relic", cascade="all, delete-orphan", lazy="raise")

    @property
    def owner_name(self) -> Optional[str]:
        return self.owner.name if self.owner else None

    @property
    def owner_public_id(self) -> Optional[str]:
        return self.owner.public_id if self.owner else None

class RelicAccess(Base):
    """
    Relic access list model.
    Tracks which users have access to a restricted relic.
    """
    __tablename__ = "relic_access"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    relic_id = Column(String(32), ForeignKey('relic.id', ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(32), ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    relic = relationship("Relic", back_populates="access_list", lazy="raise")
    user = relationship("User", backref="relic_accesses", lazy="raise")

    __table_args__ = (
        UniqueConstraint('relic_id', 'user_id', name='unique_relic_user_access'),
    )


class User(Base):
    """User identification key."""
    __tablename__ = "users"

    id = Column(String(32), primary_key=True)  # 32-char hex user ID (auth secret, never exposed)
    public_id = Column(String(16), unique=True, index=True, nullable=True)  # 16-char hex, safe to share
    name = Column(String, nullable=True)  # User's display name
    created_at = Column(DateTime, default=datetime.utcnow)
    relic_count = Column(Integer, default=0)
    # Runtime-grantable admin flag (env ADMIN_USER_IDS are immutable super-admins on top of this)
    is_admin = Column(Boolean, nullable=False, server_default=text("false"), default=False, index=True)

    # Relationships
    relics = relationship("Relic", backref=backref("owner", lazy="raise"), lazy="raise")


class Tag(Base):
    """Tag model."""
    __tablename__ = "tag"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    relics = relationship("Relic", secondary=relic_tags, back_populates="tags", lazy="raise")


class UserBookmark(Base):
    """User bookmark model - tracks which relics a user has bookmarked."""
    __tablename__ = "user_bookmark"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(32), ForeignKey('users.id'), nullable=False, index=True)
    relic_id = Column(String(32), ForeignKey('relic.id', ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", backref="bookmarks", lazy="raise")
    relic = relationship("Relic", backref=backref("bookmarked_by", passive_deletes=True, lazy="raise"), lazy="raise")

    # Unique constraint to prevent duplicate bookmarks
    __table_args__ = (
        UniqueConstraint('user_id', 'relic_id', name='unique_user_relic_bookmark'),
    )


class SavedSearch(Base):
    """
    A search a user pinned from the search bar: the query as they typed it, the list URL it
    runs on (path and query string, e.g. /recent?search=x&tag=y&sort=size-desc) and an
    optional name. Replaying one opens that URL.
    """
    __tablename__ = "saved_search"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(32), ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=True)
    query = Column(Text, nullable=False)
    path = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'path', name='unique_user_saved_search_path'),
    )


class RelicReport(Base):
    """Report model for flagging inappropriate relics."""
    __tablename__ = "relic_report"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    relic_id = Column(String(32), ForeignKey('relic.id', ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Optional: track reporter if authenticated (not strictly required by spec but good practice)
    # reporter_id = Column(String, ForeignKey('users.id'), nullable=True)

    # Relationships
    relic = relationship("Relic", backref=backref("reports", passive_deletes=True, lazy="raise"), lazy="raise")


class Comment(Base):
    """Comment model for line-specific comments on relics."""
    __tablename__ = "comment"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    relic_id = Column(String(32), ForeignKey('relic.id', ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(32), ForeignKey('users.id'), nullable=True)
    line_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    parent_id = Column(String, ForeignKey('comment.id'), nullable=True)

    # Relationships
    relic = relationship("Relic", backref=backref("comments", passive_deletes=True, lazy="raise"), lazy="raise")
    user = relationship("User", backref="comments", lazy="raise")
    replies = relationship("Comment", backref=backref("parent", remote_side=[id], lazy="raise"), cascade="all, delete-orphan", lazy="raise")


class JournalEntry(Base):
    """
    One Markdown entry of a journal.

    A journal is a relic (content type application/x-relic-journal). Each entry is a file stored
    at relics/{relic_id}/entries/{path}; this row holds what lists and searches need so they
    never have to read S3: title, date, derived counts, an excerpt and the searchable body text.
    """
    __tablename__ = "journal_entry"

    id = Column(String(32), primary_key=True)  # 32-char hex, like relic IDs
    relic_id = Column(String(32), ForeignKey('relic.id', ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String, nullable=False)  # e.g. 2026/09/2026-09-29.md, fixed at creation
    title = Column(String, nullable=False, default="")
    entry_date = Column(Date, nullable=False)
    daily = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    pinned = Column(Boolean, nullable=False, default=False, server_default=text("false"))

    # Derived from the body on every save
    excerpt = Column(String, nullable=False, default="", server_default="")
    search_text = Column(Text, nullable=False, default="", server_default="")
    word_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    open_tasks = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_tasks = Column(Integer, nullable=False, default=0, server_default=text("0"))
    size_bytes = Column(Integer, nullable=False, default=0, server_default=text("0"))

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    tags = relationship("JournalEntryTag", cascade="all, delete-orphan", lazy="raise")
    links = relationship("JournalEntryLink", cascade="all, delete-orphan", lazy="raise")

    __table_args__ = (
        UniqueConstraint('relic_id', 'path', name='uq_journal_entry_relic_path'),
        Index('ix_journal_entry_relic_date', 'relic_id', 'entry_date'),
    )

    @property
    def tag_names(self) -> list:
        return sorted(t.name for t in self.tags)


class JournalEntryTag(Base):
    """A #tag used in a journal entry. Private to the journal: it never touches the global Tag table."""
    __tablename__ = "journal_entry_tag"

    entry_id = Column(String(32), ForeignKey('journal_entry.id', ondelete="CASCADE"), primary_key=True)
    name = Column(String, primary_key=True, index=True)


class JournalEntryLink(Base):
    """A [[wiki link]] or ![[embed]] in a journal entry: what it points at (an entry title, a relic
    name or a relic ID, lowercased for matching) and the heading it sits under."""
    __tablename__ = "journal_entry_link"

    entry_id = Column(String(32), ForeignKey('journal_entry.id', ondelete="CASCADE"), primary_key=True)
    target = Column(String, primary_key=True, index=True)
    label = Column(String, nullable=False, default="", server_default="")  # the target as written
    embed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    section = Column(String, nullable=False, default="", server_default="")


class JournalEntryRevision(Base):
    """An earlier body of a journal entry, kept so an edit can be undone. Snapshots are taken when
    a save follows a pause, and only the newest few per entry are kept."""
    __tablename__ = "journal_entry_revision"

    id = Column(String(32), primary_key=True)
    entry_id = Column(String(32), ForeignKey('journal_entry.id', ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False, default="")
    body = Column(Text, nullable=False, default="")
    word_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

