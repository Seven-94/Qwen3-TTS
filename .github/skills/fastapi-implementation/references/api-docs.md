# API Documentation with OpenAPI

## Overview

FastAPI automatically generates interactive API documentation using OpenAPI (Swagger UI and ReDoc). Proper documentation makes your API easier to use and maintain.

## Basic Configuration

### Application Setup

```python
from fastapi import FastAPI

app = FastAPI(
    title="My API",
    description="A comprehensive API for managing resources",
    version="1.0.0",
    terms_of_service="https://example.com/terms",
    contact={
        "name": "API Support",
        "url": "https://example.com/support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "users",
            "description": "Operations with users",
        },
        {
            "name": "posts",
            "description": "Operations with posts",
            "externalDocs": {
                "description": "Posts documentation",
                "url": "https://example.com/docs/posts",
            },
        },
    ],
)
```

## Hide Docs in Production

```python
from fastapi import FastAPI
from src.config import settings

# Conditionally hide docs
openapi_url = "/openapi.json" if settings.ENVIRONMENT != "production" else None
docs_url = "/docs" if settings.ENVIRONMENT != "production" else None
redoc_url = "/redoc" if settings.ENVIRONMENT != "production" else None

app = FastAPI(
    title="My API",
    openapi_url=openapi_url,
    docs_url=docs_url,
    redoc_url=redoc_url,
)

# Or use a whitelist
SHOW_DOCS_ENVIRONMENTS = {"local", "development", "staging"}

app = FastAPI(
    title="My API",
    openapi_url="/openapi.json" if settings.ENVIRONMENT in SHOW_DOCS_ENVIRONMENTS else None,
)
```

## Documenting Endpoints

### Basic Endpoint Documentation

```python
from fastapi import APIRouter, status
from typing import List

router = APIRouter(prefix="/posts", tags=["posts"])

@router.get(
    "/",
    response_model=List[PostResponse],
    status_code=status.HTTP_200_OK,
    summary="List all posts",
    description="Retrieve a paginated list of all posts",
    response_description="List of posts with pagination info",
)
async def list_posts(
    skip: int = 0,
    limit: int = 100
):
    """
    List all posts with pagination.

    - **skip**: Number of posts to skip (default: 0)
    - **limit**: Maximum number of posts to return (default: 100, max: 1000)
    """
    return await get_posts(skip, limit)
```

### Detailed Endpoint Documentation

```python
from fastapi import APIRouter, status, HTTPException
from pydantic import BaseModel

class PostCreate(BaseModel):
    title: str
    content: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "My First Post",
                    "content": "This is the content of my first post."
                }
            ]
        }
    }

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "title": "My First Post",
                    "content": "This is the content of my first post.",
                    "created_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
    }

@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new post",
    description="Create a new post with the provided title and content",
    response_description="The created post",
    tags=["posts"],
    responses={
        201: {
            "description": "Post created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "title": "My First Post",
                        "content": "This is the content.",
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        400: {
            "description": "Invalid input data",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Title must not be empty"
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
    },
)
async def create_post(post: PostCreate):
    """
    Create a new post.

    This endpoint creates a new post with the following:
    - **title**: The post title (required)
    - **content**: The post content (required)

    Returns the created post with its assigned ID and timestamp.
    """
    return await create_post_in_db(post)
```

## Response Models

### Multiple Response Models

```python
from typing import Union
from fastapi import APIRouter, status

@router.get(
    "/posts/{post_id}",
    response_model=Union[PostResponse, ErrorResponse],
    responses={
        200: {
            "model": PostResponse,
            "description": "Post found",
        },
        404: {
            "model": ErrorResponse,
            "description": "Post not found",
        },
    },
)
async def get_post(post_id: int):
    """Get a post by ID."""
    post = await get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post
```

### Response Model Exclude/Include

```python
from pydantic import BaseModel

class UserFull(BaseModel):
    id: int
    username: str
    email: str
    password_hash: str
    is_active: bool

# Exclude sensitive fields
@router.get(
    "/users/{user_id}",
    response_model=UserFull,
    response_model_exclude={"password_hash"},  # Don't return password
)
async def get_user(user_id: int):
    return await get_user_by_id(user_id)

# Or include only specific fields
@router.get(
    "/users/{user_id}/public",
    response_model=UserFull,
    response_model_include={"id", "username"},  # Only public fields
)
async def get_user_public(user_id: int):
    return await get_user_by_id(user_id)
```

## Tags and Grouping

### Router Tags

```python
from fastapi import APIRouter

# All endpoints in this router get the "users" tag
users_router = APIRouter(
    prefix="/users",
    tags=["users"],
)

posts_router = APIRouter(
    prefix="/posts",
    tags=["posts"],
)

# Include routers in main app
app.include_router(users_router)
app.include_router(posts_router)
```

### Multiple Tags per Endpoint

```python
@router.get(
    "/users/{user_id}/posts",
    tags=["users", "posts"],  # Appears in both sections
    response_model=List[PostResponse],
)
async def get_user_posts(user_id: int):
    """Get all posts by a specific user."""
    return await get_posts_by_user(user_id)
```

### Tag Metadata

```python
tags_metadata = [
    {
        "name": "users",
        "description": "Operations with users. Login, registration, profile management.",
        "externalDocs": {
            "description": "External users documentation",
            "url": "https://docs.example.com/users",
        },
    },
    {
        "name": "posts",
        "description": "Manage posts. Create, read, update, and delete posts.",
    },
    {
        "name": "admin",
        "description": "Administrative operations. **Requires admin role.**",
    },
]

app = FastAPI(openapi_tags=tags_metadata)
```

## Deprecating Endpoints

```python
@router.get(
    "/old-endpoint",
    deprecated=True,
    summary="Old endpoint (deprecated)",
    description="This endpoint is deprecated. Use /new-endpoint instead.",
)
async def old_endpoint():
    """This endpoint will be removed in version 2.0. Use /new-endpoint instead."""
    return {"message": "This endpoint is deprecated"}
```

## Custom OpenAPI Schema

### Modify OpenAPI Schema

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Custom API",
        version="2.5.0",
        description="This is a custom OpenAPI schema",
        routes=app.routes,
    )

    # Add custom fields
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### Add Custom Fields to Schema

```python
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(..., example="Widget")
    description: str = Field(..., example="A useful widget")
    price: float = Field(..., gt=0, example=29.99)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Widget",
                    "description": "A useful widget",
                    "price": 29.99
                },
                {
                    "name": "Gadget",
                    "description": "An amazing gadget",
                    "price": 49.99
                }
            ]
        }
    }
```

## Authentication in Docs

### JWT Bearer Token

```python
from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

app = FastAPI()

@app.get("/protected", dependencies=[Depends(security)])
async def protected_route():
    """
    This endpoint requires a Bearer token.

    Click the "Authorize" button in Swagger UI to add your token.
    """
    return {"message": "This is protected"}
```

### OAuth2 Password Flow

```python
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

app = FastAPI()

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint for OAuth2 password flow.

    Use this endpoint to obtain an access token.
    """
    # Validate credentials and return token
    return {"access_token": "token", "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    """
    Get current user.

    Requires authentication. Use the /token endpoint to obtain a token first.
    """
    return {"token": token}
```

### API Key Authentication

```python
from fastapi import FastAPI, Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

app = FastAPI()

@app.get("/items")
async def get_items(api_key: str = Security(api_key_header)):
    """
    List items (requires API key).

    Pass your API key in the X-API-Key header.
    """
    if api_key != "secret-key":
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return {"items": []}
```

## Examples and Schemas

### Field Examples

```python
from pydantic import BaseModel, Field
from typing import List

class User(BaseModel):
    id: int = Field(..., example=1)
    username: str = Field(..., min_length=3, max_length=50, example="john_doe")
    email: str = Field(..., example="john@example.com")
    tags: List[str] = Field(default=[], example=["user", "active"])
```

### Model Examples

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    username: str
    email: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "username": "john_doe",
                    "email": "john@example.com"
                },
                {
                    "id": 2,
                    "username": "jane_smith",
                    "email": "jane@example.com"
                }
            ]
        }
    }
```

### Body Examples

```python
from fastapi import Body
from typing import Annotated

@router.post("/users")
async def create_user(
    user: Annotated[
        UserCreate,
        Body(
            examples={
                "normal": {
                    "summary": "A normal example",
                    "description": "A **normal** user creation request",
                    "value": {
                        "username": "john_doe",
                        "email": "john@example.com",
                        "password": "SecurePass123!"
                    }
                },
                "admin": {
                    "summary": "An admin example",
                    "value": {
                        "username": "admin",
                        "email": "admin@example.com",
                        "password": "AdminPass456!",
                        "role": "admin"
                    }
                },
                "invalid": {
                    "summary": "Invalid data example",
                    "value": {
                        "username": "a",  # Too short
                        "email": "not-an-email",
                        "password": "weak"
                    }
                }
            }
        )
    ]
):
    """Create a new user."""
    return await create_user_in_db(user)
```

## Error Responses

### Standard Error Model

```python
from pydantic import BaseModel
from typing import List, Optional

class ErrorDetail(BaseModel):
    loc: List[str]
    msg: str
    type: str

class ErrorResponse(BaseModel):
    detail: str | List[ErrorDetail]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Item not found"
                },
                {
                    "detail": [
                        {
                            "loc": ["body", "email"],
                            "msg": "value is not a valid email address",
                            "type": "value_error.email"
                        }
                    ]
                }
            ]
        }
    }
```

### Document All Responses

```python
from fastapi import status

@router.post(
    "/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Post created successfully",
            "model": PostResponse,
        },
        400: {
            "description": "Invalid input",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "Title cannot be empty"}
                }
            }
        },
        401: {
            "description": "Not authenticated",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        },
        403: {
            "description": "Not authorized",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "Insufficient permissions"}
                }
            }
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
    },
)
async def create_post(post: PostCreate):
    """Create a new post."""
    return await create_post_in_db(post)
```

## Documentation Best Practices

✅ **Do:**

- Provide clear summaries and descriptions
- Document all possible response codes
- Include realistic examples
- Use tags to organize endpoints
- Hide docs in production
- Document authentication requirements
- Provide external documentation links when needed
- Keep docstrings up to date

❌ **Don't:**

- Expose sensitive information in examples
- Leave default "Successful Response" descriptions
- Forget to document error responses
- Use generic descriptions
- Include implementation details in public docs
- Leave outdated documentation

## Custom Documentation UI

### Customize Swagger UI

```python
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(docs_url=None)  # Disable default docs

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,  # Hide schemas section
            "filter": True,  # Enable search
        }
    )
```

### Customize ReDoc

```python
from fastapi.openapi.docs import get_redoc_html

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )
```

## Versioning Documentation

### API Versioning

```python
from fastapi import FastAPI, APIRouter

# V1 Router
v1_router = APIRouter(prefix="/api/v1")

@v1_router.get("/users")
async def get_users_v1():
    """Get users (API v1)."""
    return []

# V2 Router
v2_router = APIRouter(prefix="/api/v2")

@v2_router.get("/users")
async def get_users_v2():
    """Get users (API v2) - includes pagination."""
    return {"users": [], "total": 0}

# Main app
app = FastAPI(title="My API")
app.include_router(v1_router, tags=["v1"])
app.include_router(v2_router, tags=["v2"])
```

## Summary

Effective API documentation in FastAPI:

1. **Configure properly** - Set meaningful title, description, version
2. **Hide in production** - Don't expose docs to public
3. **Document all responses** - Include success and error cases
4. **Provide examples** - Make it easy for users to understand
5. **Use tags** - Organize endpoints logically
6. **Keep updated** - Documentation should match implementation
7. **Add authentication info** - Make it clear what's required

Well-documented APIs are easier to use, reduce support burden, and improve developer experience.
