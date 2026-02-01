# Project Structure

## Overview

Organize FastAPI projects by **domain** rather than by file type. This scales better for monolithic applications and makes code more maintainable.

## Recommended Structure

```
fastapi-project/
├── alembic/                    # Database migrations
│   ├── versions/
│   └── env.py
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Global configuration
│   ├── models.py               # Global database models
│   ├── exceptions.py           # Global exceptions
│   ├── database.py             # Database connection
│   ├── pagination.py           # Global modules (pagination, etc.)
│   │
│   ├── auth/                   # Domain module
│   │   ├── __init__.py
│   │   ├── router.py           # API endpoints
│   │   ├── schemas.py          # Pydantic models
│   │   ├── models.py           # Database models
│   │   ├── service.py          # Business logic
│   │   ├── dependencies.py     # Route dependencies
│   │   ├── config.py           # Domain-specific config
│   │   ├── constants.py        # Constants, error codes
│   │   ├── exceptions.py       # Domain exceptions
│   │   └── utils.py            # Helper functions
│   │
│   ├── posts/                  # Another domain
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── schemas.py
│   │   ├── models.py
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   └── utils.py
│   │
│   └── aws/                    # External service integration
│       ├── __init__.py
│       ├── client.py           # Client for external service
│       ├── schemas.py
│       ├── config.py
│       ├── constants.py
│       ├── exceptions.py
│       └── utils.py
│
├── tests/                      # Mirror src/ structure
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures
│   ├── auth/
│   │   ├── test_router.py
│   │   └── test_service.py
│   ├── posts/
│   │   ├── test_router.py
│   │   └── test_service.py
│   └── aws/
│       └── test_client.py
│
├── templates/                  # HTML templates (if needed)
│   └── index.html
│
├── requirements/               # Or use pyproject.toml
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
│
├── .env                        # Environment variables
├── .env.example                # Environment variables template
├── .gitignore
├── pyproject.toml              # Project metadata & dependencies
├── alembic.ini                 # Alembic configuration
├── logging.ini                 # Logging configuration
└── README.md
```

## File Responsibilities

### Domain Module Structure

Each domain module follows a consistent pattern:

#### `router.py`

- Contains all API endpoints for the domain
- Defines path operations (`@router.get`, `@router.post`, etc.)
- Uses dependencies for validation and authentication
- Documents endpoints with OpenAPI metadata

```python
from fastapi import APIRouter, Depends, status
from . import schemas, service, dependencies

router = APIRouter(prefix="/posts", tags=["posts"])

@router.get("/{post_id}", response_model=schemas.PostResponse)
async def get_post(post: dict = Depends(dependencies.valid_post_id)):
    return post

@router.post("/", response_model=schemas.PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(data: schemas.PostCreate):
    return await service.create_post(data)
```

#### `schemas.py`

- Pydantic models for request/response validation
- Data transfer objects (DTOs)
- Type definitions

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    id: UUID
    created_at: datetime
    author_id: UUID
```

#### `models.py`

- SQLAlchemy ORM models
- Database table definitions
- Relationships between tables

```python
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base

class Post(Base):
    __tablename__ = "post"

    id = Column(UUID(as_uuid=True), primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("user.id"))
    created_at = Column(DateTime, nullable=False)
```

#### `service.py`

- Business logic
- Database operations
- External service calls
- Data processing

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas

async def create_post(db: AsyncSession, data: schemas.PostCreate, author_id: UUID):
    post = models.Post(**data.dict(), author_id=author_id)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post

async def get_by_id(db: AsyncSession, post_id: UUID):
    return await db.get(models.Post, post_id)
```

#### `dependencies.py`

- Request validation dependencies
- Authentication/authorization
- Data retrieval with validation
- Dependency injection functions

```python
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from src.database import get_db
from . import service

async def valid_post_id(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    post = await service.get_by_id(db, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return post
```

#### `config.py`

- Domain-specific configuration
- Environment variables for this domain
- Settings using Pydantic BaseSettings

```python
from pydantic_settings import BaseSettings

class PostsConfig(BaseSettings):
    MAX_POST_LENGTH: int = 10000
    POSTS_PER_PAGE: int = 20
    ENABLE_DRAFT_MODE: bool = True

    class Config:
        env_prefix = "POSTS_"

posts_config = PostsConfig()
```

#### `constants.py`

- Domain-specific constants
- Error codes
- Enums
- Default values

```python
from enum import StrEnum

class PostStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ErrorCode(StrEnum):
    POST_NOT_FOUND = "post_not_found"
    POST_ALREADY_EXISTS = "post_already_exists"
    INVALID_POST_STATUS = "invalid_post_status"

MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 50000
```

#### `exceptions.py`

- Domain-specific exceptions
- Custom error classes
- Error messages

```python
from fastapi import HTTPException, status

class PostNotFound(HTTPException):
    def __init__(self, post_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )

class PostAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Post already exists"
        )
```

#### `utils.py`

- Helper functions specific to this domain
- Data transformation utilities
- Formatting functions

```python
from datetime import datetime

def format_post_slug(title: str) -> str:
    """Convert post title to URL-friendly slug."""
    return title.lower().replace(" ", "-").replace("_", "-")

def calculate_reading_time(content: str) -> int:
    """Calculate estimated reading time in minutes."""
    words = len(content.split())
    return max(1, words // 200)  # Assume 200 words per minute
```

## Global Files

### `main.py`

Application initialization and router registration:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.auth.router import router as auth_router
from src.posts.router import router as posts_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(posts_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### `config.py`

Global application configuration:

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "My FastAPI App"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str
    REDIS_URL: str | None = None

    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"

settings = Settings()
```

### `database.py`

Database connection and session management:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
```

## Import Conventions

### Cross-Domain Imports

Use explicit module names when importing across domains to avoid confusion:

```python
# In src/posts/service.py
from src.auth import service as auth_service
from src.auth import constants as auth_constants
from src.notifications import service as notification_service

# Good - clear where it comes from
user = await auth_service.get_user_by_id(user_id)

# Bad - ambiguous
from src.auth.service import get_user_by_id
user = await get_user_by_id(user_id)  # Which domain?
```

### Intra-Domain Imports

Within the same domain, use relative imports:

```python
# In src/posts/router.py
from . import schemas, service, dependencies
from .exceptions import PostNotFound
from .constants import PostStatus
```

## Scaling Considerations

### Small Projects (< 5 domains)

- Keep all domains at the top level of `src/`
- Simple structure is sufficient

### Medium Projects (5-15 domains)

- Group related domains in subdirectories:

```
src/
├── core/          # Authentication, users, permissions
├── content/       # Posts, comments, media
├── commerce/      # Orders, payments, products
└── analytics/     # Stats, reports, metrics
```

### Large Projects (15+ domains)

- Consider microservices or modular monolith patterns
- Use clear boundaries and interfaces between modules
- Consider splitting into multiple packages

## Anti-Patterns to Avoid

❌ **Organizing by file type:**

```
src/
├── models/        # All models in one folder
├── routes/        # All routes in one folder
└── services/      # All services in one folder
```

This doesn't scale and makes it hard to understand domain boundaries.

❌ **Mixing concerns in files:**

```python
# Don't put business logic in router.py
@router.post("/posts")
async def create_post(data: PostCreate):
    # Business logic here (BAD)
    db_post = Post(**data.dict())
    db.add(db_post)
    await db.commit()
    return db_post
```

❌ **Circular imports:**

```python
# src/posts/service.py imports from src/users/service.py
# src/users/service.py imports from src/posts/service.py
# This creates circular dependency issues
```

❌ **God modules:**

- Avoid having one giant `utils.py` or `helpers.py`
- Keep utilities close to where they're used
- If used across domains, consider a dedicated module

## Benefits of Domain-Based Structure

✅ **Clear boundaries** - Each domain is self-contained  
✅ **Easy to navigate** - Related code is grouped together  
✅ **Scalable** - Add new domains without restructuring  
✅ **Testable** - Test domains in isolation  
✅ **Team-friendly** - Different teams can own different domains  
✅ **Maintainable** - Changes are localized to specific domains

## Migration from Type-Based Structure

If migrating from a type-based structure:

1. Identify your domains (e.g., auth, posts, users, payments)
2. Create domain folders in `src/`
3. Move related files into domain folders
4. Update imports to use explicit module names
5. Test thoroughly after migration
6. Update documentation

Example migration:

```bash
# Before
src/models/user.py
src/routes/user.py
src/services/user.py

# After
src/users/models.py
src/users/router.py
src/users/service.py
```
