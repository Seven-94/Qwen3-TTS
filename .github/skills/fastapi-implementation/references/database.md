# Database Configuration and Best Practices

## Overview

Database setup in FastAPI requires careful attention to naming conventions, connection management, and migration strategies.

## SQLAlchemy Setup (Async)

### Database Connection

```python
# src/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
from src.config import settings

# Naming convention for database constraints
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)
Base = declarative_base(metadata=metadata)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Dependency for getting database session
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Configuration Settings

```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@localhost/dbname
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # Recycle connections after 30 min

    DEBUG: bool = False

settings = Settings()
```

## Naming Conventions

### Table Names

Follow these conventions for consistency:

```python
# ✅ Good naming
class User(Base):
    __tablename__ = "user"  # Singular, lowercase, snake_case

class PostLike(Base):
    __tablename__ = "post_like"  # Singular concept, snake_case

class PaymentAccount(Base):
    __tablename__ = "payment_account"  # Group with prefix

class PaymentBill(Base):
    __tablename__ = "payment_bill"  # Same domain prefix

# ❌ Bad naming
class Users(Base):
    __tablename__ = "Users"  # Plural, PascalCase (inconsistent)

class post_likes(Base):
    __tablename__ = "PostLikes"  # Inconsistent casing
```

### Column Names

```python
from sqlalchemy import Column, String, Integer, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class User(Base):
    __tablename__ = "user"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # String fields - snake_case
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(100))

    # Boolean fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # DateTime fields - suffix with _at
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    verified_at = Column(DateTime)

    # Date fields - suffix with _date
    birth_date = Column(Date)
    subscription_start_date = Column(Date)

    # Foreign keys - suffix with _id, reference table name
    role_id = Column(UUID(as_uuid=True), ForeignKey("role.id"))
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("user.id"))
```

### Naming Convention Summary

| Type              | Convention                   | Example                                  |
| ----------------- | ---------------------------- | ---------------------------------------- |
| Table             | `lower_case_snake`, singular | `user`, `post_like`, `payment_account`   |
| Column            | `lower_case_snake`           | `username`, `email_address`              |
| DateTime          | suffix `_at`                 | `created_at`, `updated_at`, `deleted_at` |
| Date              | suffix `_date`               | `birth_date`, `expiry_date`              |
| Boolean           | prefix `is_`, `has_`, `can_` | `is_active`, `has_subscription`          |
| Foreign Key       | suffix `_id`                 | `user_id`, `post_id`, `author_id`        |
| Index             | auto-generated               | `email_idx` (via naming convention)      |
| Unique constraint | auto-generated               | `user_email_key`                         |

## Model Relationships

### One-to-Many

```python
from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

class User(Base):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)

    # Relationship
    posts = relationship("Post", back_populates="author", lazy="selectin")

class Post(Base):
    __tablename__ = "post"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    # Foreign key
    author_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)

    # Relationship
    author = relationship("User", back_populates="posts")
```

### Many-to-Many

```python
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

# Association table
post_tag_association = Table(
    'post_tag',
    Base.metadata,
    Column('post_id', UUID(as_uuid=True), ForeignKey('post.id'), primary_key=True),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tag.id'), primary_key=True),
)

class Post(Base):
    __tablename__ = "post"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)

    # Many-to-many relationship
    tags = relationship(
        "Tag",
        secondary=post_tag_association,
        back_populates="posts",
        lazy="selectin"
    )

class Tag(Base):
    __tablename__ = "tag"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)

    # Many-to-many relationship
    posts = relationship(
        "Post",
        secondary=post_tag_association,
        back_populates="tags",
        lazy="selectin"
    )
```

## Indexes

### Creating Indexes

```python
from sqlalchemy import Column, String, Index

class User(Base):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Simple index (on single column)
    __table_args__ = (
        Index('user_email_idx', 'email'),  # Explicit name (or use index=True in Column)
        Index('user_created_at_idx', 'created_at'),
    )

class Post(Base):
    __tablename__ = "post"

    id = Column(UUID(as_uuid=True), primary_key=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("user.id"))
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite index (multiple columns)
    __table_args__ = (
        Index('post_author_status_idx', 'author_id', 'status'),
        Index('post_status_created_idx', 'status', 'created_at'),
    )
```

### Partial Indexes (PostgreSQL)

```python
from sqlalchemy import Index

class User(Base):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String(255), unique=True)
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime)

    # Partial index - only index active users
    __table_args__ = (
        Index(
            'active_users_email_idx',
            'email',
            postgresql_where=(Column('is_active') == True)
        ),
        # Only index non-deleted users
        Index(
            'non_deleted_users_idx',
            'email',
            postgresql_where=(Column('deleted_at').is_(None))
        ),
    )
```

## Query Patterns

### SQL-First Approach

For complex queries, use SQL directly for better performance:

```python
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_stats(db: AsyncSession, user_id: UUID):
    """Use SQL for complex aggregations."""
    query = text("""
        SELECT
            u.id,
            u.username,
            COUNT(DISTINCT p.id) as post_count,
            COUNT(DISTINCT c.id) as comment_count,
            AVG(p.view_count) as avg_views
        FROM "user" u
        LEFT JOIN post p ON p.author_id = u.id
        LEFT JOIN comment c ON c.user_id = u.id
        WHERE u.id = :user_id
        GROUP BY u.id, u.username
    """)

    result = await db.execute(query, {"user_id": user_id})
    return result.fetchone()
```

### JSON Aggregation (PostgreSQL)

Build nested JSON responses in the database:

```python
async def get_posts_with_comments(db: AsyncSession, limit: int = 10):
    """Return posts with nested comments as JSON."""
    query = text("""
        SELECT
            json_build_object(
                'id', p.id,
                'title', p.title,
                'content', p.content,
                'author', json_build_object(
                    'id', u.id,
                    'username', u.username
                ),
                'comments', COALESCE(
                    json_agg(
                        json_build_object(
                            'id', c.id,
                            'text', c.text,
                            'author', c.author_username
                        )
                        ORDER BY c.created_at DESC
                    ) FILTER (WHERE c.id IS NOT NULL),
                    '[]'::json
                )
            ) as post_json
        FROM post p
        JOIN "user" u ON u.id = p.author_id
        LEFT JOIN comment c ON c.post_id = p.id
        GROUP BY p.id, u.id
        ORDER BY p.created_at DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"limit": limit})
    return [row[0] for row in result.fetchall()]
```

### Async ORM Queries

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Simple query
async def get_user_by_id(db: AsyncSession, user_id: UUID):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

# Query with filter
async def get_active_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(User)
        .where(User.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

# Query with join
async def get_posts_with_author(db: AsyncSession):
    result = await db.execute(
        select(Post, User)
        .join(User, Post.author_id == User.id)
        .where(Post.status == "published")
    )
    return result.all()

# Query with aggregation
async def count_posts_by_user(db: AsyncSession, user_id: UUID):
    result = await db.execute(
        select(func.count(Post.id))
        .where(Post.author_id == user_id)
    )
    return result.scalar()
```

## Migrations with Alembic

### Setup

```bash
# Install alembic
pip install alembic

# Initialize alembic
alembic init alembic
```

### Configuration

```ini
# alembic.ini
[alembic]
# Use date-based file naming
file_template = %%(year)d-%%(month).2d-%%(day).2d_%%(slug)s

script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://user:password@localhost/dbname
```

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from src.database import Base
from src.config import settings

# Import all models to ensure they're registered
from src.auth.models import *
from src.posts.models import *

config = context.config

# Set database URL from settings
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
```

### Creating Migrations

```bash
# Auto-generate migration from models
alembic revision --autogenerate -m "add_user_table"

# Create empty migration (manual)
alembic revision -m "add_custom_index"

# Result: alembic/versions/2024-01-15_add_user_table.py
```

### Migration File Best Practices

```python
"""add user table

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2024-01-15 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = 'abc123def456'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Upgrade schema."""
    # Create table
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create indexes
    op.create_index('user_email_idx', 'user', ['email'], unique=True)
    op.create_index('user_username_idx', 'user', ['username'], unique=True)

def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('user_username_idx', table_name='user')
    op.drop_index('user_email_idx', table_name='user')

    # Drop table
    op.drop_table('user')
```

### Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade abc123def456

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade xyz789

# Show current revision
alembic current

# Show migration history
alembic history

# Show SQL without applying (dry-run)
alembic upgrade head --sql
```

### Migration Best Practices

✅ **Do:**

- Use descriptive migration names with dates
- Make migrations reversible (implement `downgrade()`)
- Keep migrations static (no dynamic data)
- Test migrations on a copy of production data
- Review auto-generated migrations before applying
- Add data migrations in separate files from schema changes
- Use batch operations for large table modifications

❌ **Don't:**

- Edit applied migrations (create new ones instead)
- Mix schema and data changes in one migration
- Delete migration files
- Rely solely on auto-generated migrations (review first!)
- Run migrations directly on production (test first!)

### Data Migration Example

```python
"""populate default roles

Revision ID: def456ghi789
Revises: abc123def456
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    """Insert default roles."""
    # Use op.bulk_insert for better performance
    roles_table = sa.table(
        'role',
        sa.column('id', sa.UUID),
        sa.column('name', sa.String),
        sa.column('description', sa.String),
    )

    op.bulk_insert(
        roles_table,
        [
            {'name': 'admin', 'description': 'Administrator'},
            {'name': 'user', 'description': 'Regular user'},
            {'name': 'moderator', 'description': 'Content moderator'},
        ]
    )

def downgrade() -> None:
    """Remove default roles."""
    op.execute("DELETE FROM role WHERE name IN ('admin', 'user', 'moderator')")
```

## Connection Pooling

### Configure Pool Settings

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,

    # Pool size
    pool_size=5,                    # Number of connections to keep
    max_overflow=10,                # Additional connections if pool full

    # Pool behavior
    pool_timeout=30,                # Seconds to wait for connection
    pool_recycle=1800,              # Recycle connections after 30 min
    pool_pre_ping=True,             # Verify connection before using

    # Echo SQL queries (debug mode)
    echo=False,

    # Async execution
    future=True,
)
```

### Pool Monitoring

```python
from sqlalchemy import event
from sqlalchemy.pool import Pool
import logging

logger = logging.getLogger(__name__)

@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.info("New connection established")

@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("Connection checked out from pool")

@event.listens_for(Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    logger.debug("Connection returned to pool")
```

## Best Practices Summary

### Database Design

- Use singular table names: `user`, not `users`
- Use snake_case for all names
- Suffix datetime fields with `_at`
- Suffix date fields with `_date`
- Prefix boolean fields with `is_`, `has_`, `can_`
- Group related tables with prefixes: `payment_account`, `payment_bill`

### Performance

- Use indexes on frequently queried columns
- Use composite indexes for multi-column queries
- Use partial indexes for conditional queries
- Prefer SQL for complex aggregations
- Use JSON aggregation for nested data
- Configure connection pooling appropriately

### Migrations

- Use descriptive names with dates
- Keep migrations reversible
- Test on production-like data
- Review auto-generated migrations
- Separate schema and data migrations

### Code Quality

- Use async database drivers (asyncpg, motor, etc.)
- Set explicit naming conventions for constraints
- Implement proper session management with yield
- Use transactions for multi-step operations
- Handle connection errors gracefully

## Transactions

### Manual Transaction Control

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def transfer_funds(
    db: AsyncSession,
    from_account_id: UUID,
    to_account_id: UUID,
    amount: float
):
    """Transfer funds between accounts (atomic operation)."""
    async with db.begin():  # Explicit transaction
        # Debit from account
        from_account = await db.get(Account, from_account_id)
        from_account.balance -= amount

        # Credit to account
        to_account = await db.get(Account, to_account_id)
        to_account.balance += amount

        # Both changes committed together or rolled back on error
```

### Savepoints

```python
async def complex_operation(db: AsyncSession):
    """Use savepoints for nested transactions."""
    async with db.begin():
        # Main transaction
        user = User(username="test")
        db.add(user)

        async with db.begin_nested():  # Savepoint
            # This can be rolled back independently
            profile = Profile(user_id=user.id)
            db.add(profile)

            if not valid:
                # Rolls back only to savepoint
                raise Exception("Profile invalid")

        # Main transaction continues
```

## Summary

Effective database management in FastAPI requires:

1. **Consistent naming** for maintainability
2. **Proper indexing** for performance
3. **SQL-first approach** for complex queries
4. **Well-organized migrations** for schema evolution
5. **Connection pooling** for scalability
6. **Transaction management** for data integrity

Follow these patterns to build robust, scalable database layers in your FastAPI applications.
