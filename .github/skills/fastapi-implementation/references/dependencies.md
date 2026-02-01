# Dependencies

## Overview

FastAPI dependencies are far more powerful than simple dependency injection. Use them for validation, authentication, data retrieval, and complex request processing.

## Core Concepts

### 1. Dependencies are Functions

Dependencies are simply callable functions that FastAPI executes before your route handler:

```python
from fastapi import Depends, APIRouter

router = APIRouter()

async def common_parameters(skip: int = 0, limit: int = 100):
    """Simple dependency that returns query parameters."""
    return {"skip": skip, "limit": limit}

@router.get("/items")
async def read_items(commons: dict = Depends(common_parameters)):
    return commons
```

### 2. Dependencies are Cached Per Request

FastAPI caches dependency results **within a single request**. If the same dependency is called multiple times in one request (across different dependencies or directly), it executes **only once**.

```python
async def get_db():
    print("Opening database connection")
    db = await connect_to_database()
    yield db
    await db.close()

# Called in multiple places but executes once per request
@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db1: Database = Depends(get_db),  # Executes get_db()
    db2: Database = Depends(get_db),  # Reuses cached connection
):
    # db1 and db2 are the same instance
    pass
```

### 3. Dependencies Can Yield (Context Managers)

Use `yield` for setup/teardown patterns:

```python
async def get_db():
    db = await create_connection()
    try:
        yield db  # Request processing happens here
    finally:
        await db.close()  # Always runs, even on errors
```

## Beyond Dependency Injection: Validation

### Pattern 1: Validate Request Data Against Database

Instead of just providing a database connection, dependencies can validate that referenced entities exist:

```python
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

async def valid_post_id(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Validate post exists and return it."""
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )
    return post

@router.get("/posts/{post_id}")
async def get_post(post: dict = Depends(valid_post_id)):
    """Route receives already-validated post data."""
    return post

@router.put("/posts/{post_id}")
async def update_post(
    update_data: PostUpdate,
    post: dict = Depends(valid_post_id)  # Reuse validation
):
    updated = await service.update(post["id"], update_data)
    return updated

@router.delete("/posts/{post_id}")
async def delete_post(post: dict = Depends(valid_post_id)):
    await service.delete(post["id"])
    return {"success": True}
```

**Benefits:**

- ✅ No duplicate validation in each route
- ✅ Automatic 404 responses for invalid IDs
- ✅ Cleaner route handlers
- ✅ Easier testing (mock the dependency)

### Pattern 2: Validate Related Entities

```python
async def valid_comment_id(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Validate comment exists."""
    comment = await db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment

async def valid_post_has_comment(
    post: dict = Depends(valid_post_id),
    comment: dict = Depends(valid_comment_id)
) -> tuple[dict, dict]:
    """Validate comment belongs to post."""
    if comment["post_id"] != post["id"]:
        raise HTTPException(
            status_code=400,
            detail="Comment does not belong to this post"
        )
    return post, comment

@router.get("/posts/{post_id}/comments/{comment_id}")
async def get_comment(
    data: tuple[dict, dict] = Depends(valid_post_has_comment)
):
    post, comment = data
    return comment
```

## Chaining Dependencies

Dependencies can depend on other dependencies, creating validation chains:

```python
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

# Level 1: Extract token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Level 2: Parse and validate JWT
async def parse_jwt_data(token: str = Depends(oauth2_scheme)) -> dict:
    """Extract user ID from JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Level 3: Get current user from database
async def get_current_user(
    token_data: dict = Depends(parse_jwt_data),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get user object from database."""
    user = await db.get(User, token_data["user_id"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Level 4: Verify user is active
async def get_current_active_user(
    user: User = Depends(get_current_user)
) -> User:
    """Verify user account is active."""
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

# Level 5: Verify user has specific role
def require_role(required_role: str):
    """Dependency factory for role-based access."""
    async def check_role(user: User = Depends(get_current_active_user)) -> User:
        if user.role != required_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_role

# Usage in routes
@router.get("/public")
async def public_endpoint():
    return {"message": "Everyone can access"}

@router.get("/protected")
async def protected_endpoint(user: User = Depends(get_current_user)):
    return {"user": user.username}

@router.get("/admin")
async def admin_endpoint(user: User = Depends(require_role("admin"))):
    return {"message": "Admin access granted"}
```

**Key Points:**

- Each level builds on the previous
- Earlier dependencies run first
- Results are cached per request
- Failures stop the chain immediately

## Decouple & Reuse Dependencies

### Consistent Path Variable Names

For dependency reuse, use consistent path variable names:

```python
# Good - both use 'profile_id'
@router.get("/profiles/{profile_id}")
async def get_profile(profile: dict = Depends(valid_profile_id)):
    pass

@router.get("/creators/{profile_id}")  # Same variable name!
async def get_creator(profile: dict = Depends(valid_creator_id)):
    # valid_creator_id can use valid_profile_id internally
    pass

# Bad - different variable names
@router.get("/profiles/{profile_id}")
@router.get("/creators/{creator_id}")  # Can't share dependencies easily
```

### Dependency Pattern

```python
# Base validation
async def valid_profile_id(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

# Extended validation (chains base)
async def valid_creator_id(
    profile: dict = Depends(valid_profile_id)  # Reuses validation!
) -> dict:
    if not profile["is_creator"]:
        raise HTTPException(status_code=400, detail="Profile is not a creator")
    return profile

# Usage
@router.get("/profiles/{profile_id}")
async def get_profile(profile: dict = Depends(valid_profile_id)):
    return profile

@router.get("/creators/{profile_id}")
async def get_creator(creator: dict = Depends(valid_creator_id)):
    return creator
```

## Prefer Async Dependencies

Use `async def` for dependencies whenever possible:

```python
# ✅ Good - async dependency
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    user = await db.get_user_by_token(token)
    return user

# ❌ Less optimal - sync dependency
def get_current_user_sync(token: str = Depends(oauth2_scheme)) -> User:
    user = db.get_user_by_token_sync(token)  # Runs in threadpool
    return user
```

**Why prefer async:**

- No threadpool overhead for simple operations
- Better performance at scale
- Consistent with FastAPI's async-first design

**When sync is acceptable:**

- Dependency has no I/O (pure computation)
- Using sync-only library with no async alternative
- Very light operations where threadpool overhead is negligible

## Class-Based Dependencies

For dependencies with state or configuration:

```python
from typing import Optional

class Pagination:
    def __init__(
        self,
        skip: int = 0,
        limit: int = 100,
        max_limit: int = 1000
    ):
        self.skip = skip
        self.limit = min(limit, max_limit)  # Enforce max

# Use as dependency
@router.get("/items")
async def list_items(pagination: Pagination = Depends()):
    return await get_items(pagination.skip, pagination.limit)

# With custom configuration
class AdminPagination(Pagination):
    def __init__(self, skip: int = 0, limit: int = 1000):
        super().__init__(skip, limit, max_limit=10000)  # Higher max for admins

@router.get("/admin/items")
async def list_all_items(
    user: User = Depends(require_role("admin")),
    pagination: AdminPagination = Depends()
):
    return await get_items(pagination.skip, pagination.limit)
```

## Global Dependencies

Apply dependencies to all routes in a router or app:

```python
from fastapi import FastAPI, APIRouter, Depends

# Router-level dependencies
router = APIRouter(
    prefix="/api",
    dependencies=[Depends(get_current_active_user)]  # All routes require auth
)

@router.get("/items")  # Automatically requires auth
async def get_items():
    pass

# App-level dependencies
app = FastAPI(dependencies=[Depends(log_requests)])

# All routes in the app will run log_requests dependency
```

## Dependency with Yield (Setup/Teardown)

### Database Session Management

```python
async def get_db() -> AsyncSession:
    """Provide database session with automatic cleanup."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()  # Auto-commit on success
        except Exception:
            await session.rollback()  # Auto-rollback on error
            raise
        finally:
            await session.close()  # Always close

@router.post("/items")
async def create_item(
    item: ItemCreate,
    db: AsyncSession = Depends(get_db)  # Auto-managed
):
    db_item = Item(**item.dict())
    db.add(db_item)
    # No need to commit/close - handled by dependency
    return db_item
```

### Background Tasks with Cleanup

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_redis():
    """Redis connection with cleanup."""
    redis = await aioredis.create_redis_pool('redis://localhost')
    try:
        yield redis
    finally:
        redis.close()
        await redis.wait_closed()

async def get_cache():
    async with get_redis() as redis:
        yield redis

@router.get("/cached-data")
async def get_cached_data(cache = Depends(get_cache)):
    data = await cache.get("key")
    return data
```

## Dependencies in Path Operation Decorators

Use dependencies for side effects (logging, rate limiting) without needing their return value:

```python
async def verify_token(x_token: str = Header()):
    """Verify token but don't return anything."""
    if x_token != "secret-token":
        raise HTTPException(status_code=400, detail="Invalid X-Token")

async def verify_key(x_key: str = Header()):
    """Verify API key."""
    if x_key != "secret-key":
        raise HTTPException(status_code=400, detail="Invalid X-Key")

@router.get(
    "/items",
    dependencies=[Depends(verify_token), Depends(verify_key)]  # Both required
)
async def read_items():
    return [{"item": "Foo"}, {"item": "Bar"}]
```

## Sub-Dependencies

Dependencies can have their own dependencies:

```python
async def get_db():
    # Database connection
    yield db

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)  # Sub-dependency
):
    # Uses db from get_db
    user = await db.get_user_by_token(token)
    return user

async def get_admin_user(
    user: User = Depends(get_current_user)  # Which uses get_db
):
    if not user.is_admin:
        raise HTTPException(status_code=403)
    return user

# Route implicitly uses: oauth2_scheme -> get_db -> get_current_user -> get_admin_user
@router.get("/admin/data")
async def admin_data(admin: User = Depends(get_admin_user)):
    return {"admin": admin.username}
```

## Parameterized Dependencies

Create dependency factories for configurable dependencies:

```python
def get_query_checker(min_length: int = 3):
    """Factory that returns a dependency function."""
    async def check_query(q: str = Query(...)):
        if len(q) < min_length:
            raise HTTPException(
                status_code=400,
                detail=f"Query must be at least {min_length} characters"
            )
        return q
    return check_query

# Use with different configurations
@router.get("/search")
async def search(query: str = Depends(get_query_checker(min_length=3))):
    return {"query": query}

@router.get("/advanced-search")
async def advanced_search(query: str = Depends(get_query_checker(min_length=5))):
    return {"query": query}
```

### Permission Checker Factory

```python
from enum import Enum

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

def require_permission(required: Permission):
    """Dependency factory for permission checking."""
    async def check_permission(
        user: User = Depends(get_current_active_user)
    ) -> User:
        if required not in user.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {required} required"
            )
        return user
    return check_permission

# Usage
@router.get("/posts")
async def read_posts(user: User = Depends(require_permission(Permission.READ))):
    return await get_posts()

@router.post("/posts")
async def create_post(
    post: PostCreate,
    user: User = Depends(require_permission(Permission.WRITE))
):
    return await create_post_for_user(user, post)

@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: UUID,
    user: User = Depends(require_permission(Permission.DELETE))
):
    return await delete_post_by_id(post_id)
```

## Advanced Patterns

### Conditional Dependencies

```python
from fastapi import Request

async def get_user_if_authenticated(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """Return user if authenticated, None otherwise (no error)."""
    token = request.headers.get("Authorization")
    if not token:
        return None

    try:
        user = await get_user_from_token(token, db)
        return user
    except:
        return None

@router.get("/posts")
async def list_posts(user: User | None = Depends(get_user_if_authenticated)):
    """Show all posts, with user-specific data if authenticated."""
    if user:
        return await get_posts_for_user(user)
    return await get_public_posts()
```

### Composite Dependencies

```python
from typing import NamedTuple

class RequestContext(NamedTuple):
    """Bundle of commonly needed dependencies."""
    user: User
    db: AsyncSession
    cache: Redis

async def get_request_context(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    cache: Redis = Depends(get_cache)
) -> RequestContext:
    """Provide all common dependencies in one."""
    return RequestContext(user=user, db=db, cache=cache)

@router.get("/dashboard")
async def dashboard(ctx: RequestContext = Depends(get_request_context)):
    """Route gets all context at once."""
    # Use ctx.user, ctx.db, ctx.cache
    return await build_dashboard(ctx.user, ctx.db, ctx.cache)
```

### Dependency Override (Testing)

```python
from fastapi.testclient import TestClient

# Production dependency
async def get_db():
    db = ProductionDB()
    yield db
    await db.close()

# Test override
async def get_test_db():
    db = TestDB()
    yield db
    await db.close()

# In tests
def test_create_user():
    app.dependency_overrides[get_db] = get_test_db

    client = TestClient(app)
    response = client.post("/users", json={"username": "test"})

    assert response.status_code == 200

    # Cleanup
    app.dependency_overrides.clear()
```

## Performance Considerations

### Dependency Caching

```python
# This executes ONCE per request, even if used multiple times
async def expensive_operation():
    print("Computing...")
    result = await heavy_computation()
    return result

@router.get("/data")
async def get_data(
    result1: dict = Depends(expensive_operation),  # Computes
    result2: dict = Depends(expensive_operation),  # Cached (same instance)
):
    # result1 and result2 are the same object
    return {"r1": result1, "r2": result2}
```

### Disable Caching (Rarely Needed)

```python
from fastapi import Depends

async def no_cache_operation():
    return await get_fresh_data()

# Force re-execution each time
@router.get("/data")
async def get_data(
    data1: dict = Depends(no_cache_operation, use_cache=False),
    data2: dict = Depends(no_cache_operation, use_cache=False),
):
    # data1 and data2 are different (computed twice)
    return {"d1": data1, "d2": data2}
```

## Best Practices

✅ **Do:**

- Use dependencies for validation, not just DI
- Chain dependencies for complex validation
- Prefer async dependencies
- Use consistent path variable names
- Cache dependencies per request
- Use dependency factories for configurable checks
- Leverage yield for setup/teardown
- Test dependencies in isolation

❌ **Don't:**

- Put business logic in dependencies (keep them focused)
- Create circular dependencies
- Overuse complex dependency chains (keep it readable)
- Ignore dependency execution order
- Forget that dependencies are cached per request
- Use dependencies for heavy computation (offload to workers)

## Common Patterns Summary

| Pattern        | Use Case                 | Example                                |
| -------------- | ------------------------ | -------------------------------------- |
| Validation     | Verify entity exists     | `valid_post_id`                        |
| Authentication | Extract/verify user      | `get_current_user`                     |
| Authorization  | Check permissions        | `require_role("admin")`                |
| Chain          | Build on previous checks | `valid_owned_post`                     |
| Factory        | Configurable behavior    | `require_permission(Permission.WRITE)` |
| Yield          | Setup/teardown           | `get_db` session                       |
| Global         | Apply to all routes      | Router-level dependencies              |
| Conditional    | Optional behavior        | `get_user_if_authenticated`            |
| Composite      | Bundle dependencies      | `RequestContext`                       |

## Debugging Dependencies

### Log Dependency Execution

```python
import logging

logger = logging.getLogger(__name__)

async def logged_dependency(x: int):
    logger.info(f"Dependency executing with x={x}")
    result = await process(x)
    logger.info(f"Dependency completed with result={result}")
    return result
```

### Inspect Dependency Graph

```python
from fastapi import FastAPI
from fastapi.routing import APIRoute

app = FastAPI()

for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"Route: {route.path}")
        print(f"Dependencies: {route.dependencies}")
```

## Summary

Dependencies are one of FastAPI's most powerful features:

- **Validation**: Check data against database before route runs
- **Authentication**: Extract and verify user identity
- **Authorization**: Enforce permissions
- **Chaining**: Build complex validation pipelines
- **Caching**: Execute once per request, reuse everywhere
- **Reusability**: Share validation logic across routes
- **Testability**: Easy to mock and override

Use dependencies aggressively to keep your route handlers clean and focused on business logic.
