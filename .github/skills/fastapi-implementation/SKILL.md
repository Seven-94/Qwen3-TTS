---
name: fastapi-implementation
description: Implement production-ready FastAPI applications following modern best practices. Use this skill when building REST APIs with FastAPI, structuring API projects, implementing async routes, working with Pydantic validation, setting up dependencies, configuring databases with migrations, adding tests, or documenting APIs. Covers project structure, async/sync patterns, validation, dependency injection, error handling, database conventions, and testing.
license: Complete terms in LICENSE.txt
---

# FastAPI Implementation

This skill provides comprehensive guidance for implementing production-ready FastAPI applications using modern best practices.

## When to Use This Skill

Use this skill when:

- Building a new FastAPI project from scratch
- Structuring an existing FastAPI application
- Implementing async/sync routes correctly
- Setting up Pydantic models and validation
- Working with dependencies and dependency injection
- Configuring database connections and migrations
- Writing tests for FastAPI applications
- Setting up API documentation
- Handling errors and exceptions
- Optimizing performance

## Quick Start

For a new FastAPI project, start with:

1. **Project Structure**: See `references/project-structure.md` for recommended folder organization
2. **Basic Setup**: Use `assets/quickstart-template/` as a starting point
3. **Configuration**: Set up environment variables with Pydantic BaseSettings

## Key Principles

### 1. Async-First Philosophy

FastAPI is async-first. Use `async def` for routes with non-blocking I/O operations, `def` for blocking operations (runs in threadpool).

### 2. Leverage Pydantic

Pydantic provides powerful validation. Use it extensively for request/response models, configuration, and data validation.

### 3. Dependencies for Validation

Dependencies aren't just for DI—use them for request validation, authentication, and data retrieval.

### 4. Domain-Based Structure

Organize code by domain (e.g., `auth/`, `posts/`, `users/`) rather than by file type (e.g., `models/`, `routes/`).

### 5. Explicit Over Implicit

- Set explicit naming conventions for database indexes
- Use explicit response models and status codes
- Document all endpoints with proper OpenAPI metadata

## Core Concepts

### Route Types

```python
# Async route - for non-blocking I/O
@router.get("/items")
async def get_items():
    items = await db.fetch_all()  # Non-blocking
    return items

# Sync route - for blocking operations (runs in threadpool)
@router.get("/items")
def get_items():
    items = blocking_db_call()  # Blocking but isolated
    return items
```

### Dependency Injection & Validation

```python
# Dependency validates data and retrieves from DB
async def valid_post_id(post_id: UUID4) -> dict:
    post = await service.get_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

# Route uses validated data
@router.get("/posts/{post_id}")
async def get_post(post: dict = Depends(valid_post_id)):
    return post
```

### Pydantic Models

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=128, pattern="^[A-Za-z0-9-_]+$")
    email: EmailStr
    age: int = Field(ge=18)
```

## Detailed Guides

Each topic has a dedicated reference file with detailed instructions:

- **Project Structure**: `references/project-structure.md` - Folder organization and import conventions
- **Async/Sync Routes**: `references/async-sync.md` - When to use async vs sync, common pitfalls
- **Pydantic**: `references/pydantic.md` - Validation, schemas, custom base models, BaseSettings
- **Dependencies**: `references/dependencies.md` - DI patterns, validation, chaining, caching
- **Database**: `references/database.md` - Naming conventions, migrations, query patterns
- **Testing**: `references/testing.md` - AsyncClient setup, fixtures, test patterns
- **API Documentation**: `references/api-docs.md` - OpenAPI customization, response models
- **Error Handling**: `references/error-handling.md` - Custom exceptions, handlers, validation errors

## Common Patterns

### 1. Custom Base Model

Create a shared Pydantic base model for consistent behavior:

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class CustomModel(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        populate_by_name=True,
    )
```

### 2. Split Configuration by Domain

```python
# src/auth/config.py
from pydantic_settings import BaseSettings

class AuthConfig(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

auth_config = AuthConfig()
```

### 3. Chain Dependencies

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Validate token and return user
    pass

async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

### 4. Use run_in_threadpool for Sync Libraries

```python
from fastapi.concurrency import run_in_threadpool

@router.post("/process")
async def process_data(data: DataModel):
    result = await run_in_threadpool(sync_library.process, data.dict())
    return result
```

## Quick Reference

| Scenario                      | Solution                               |
| ----------------------------- | -------------------------------------- |
| Non-blocking I/O              | `async def` route with `await` calls   |
| Blocking I/O                  | `def` route (sync, runs in threadpool) |
| Sync library in async context | Use `run_in_threadpool()`              |
| CPU-intensive work            | Offload to Celery or multiprocessing   |
| Request validation            | Use dependencies with DB checks        |
| Shared validation logic       | Chain dependencies                     |
| Config per domain             | Separate `BaseSettings` classes        |
| Complex DB queries            | Use SQL with JSON aggregation          |
| Multiple responses            | Document with `responses` parameter    |
| Hide docs in prod             | Set `openapi_url=None` conditionally   |

## Anti-Patterns to Avoid

❌ **Blocking calls in async routes**

```python
@router.get("/bad")
async def bad_route():
    time.sleep(10)  # Blocks event loop!
```

❌ **Organizing by file type instead of domain**

```
src/
  models/      # Don't do this
  routes/
  services/
```

❌ **Not using response_model**

```python
@router.get("/items")  # Missing response_model
async def get_items():
    return items
```

❌ **Ignoring dependency caching**

- FastAPI caches dependency results per request
- Reuse dependencies instead of duplicating logic

❌ **Manual validation instead of Pydantic**

```python
# Bad
if not email or "@" not in email:
    raise ValueError("Invalid email")

# Good
from pydantic import EmailStr
email: EmailStr
```

## Resources

- Official FastAPI docs: https://fastapi.tiangolo.com
- FastAPI GitHub: https://github.com/fastapi/fastapi
- Pydantic docs: https://docs.pydantic.dev

## Getting Help

When working with this skill:

1. Check the specific reference file for your topic
2. Use the quickstart template for new projects
3. Follow the patterns shown in examples
4. Reference the Quick Reference table for common scenarios

## Linting & Code Quality

Use `ruff` for formatting and linting:

```bash
ruff check --fix src
ruff format src
```

## Environment Setup

```python
# .env file
DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ENVIRONMENT=development
```

## Project Initialization

When starting a new FastAPI project:

1. Copy `assets/quickstart-template/` as base
2. Read `references/project-structure.md` for organization
3. Set up configuration with domain-specific BaseSettings
4. Configure database with naming conventions
5. Set up tests with AsyncClient
6. Configure API docs for your environment

This skill focuses on practical, production-ready patterns that scale from small APIs to large monolithic applications.
