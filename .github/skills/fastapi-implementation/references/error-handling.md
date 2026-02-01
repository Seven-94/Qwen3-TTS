# Error Handling and Exception Management

## Overview

Proper error handling ensures your API provides clear, consistent, and secure error responses to clients.

## HTTP Exceptions

### Basic HTTPException

```python
from fastapi import FastAPI, HTTPException, status

app = FastAPI()

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = await get_item_from_db(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return item
```

### HTTPException with Headers

```python
from fastapi import HTTPException

@app.get("/restricted")
async def restricted_access():
    raise HTTPException(
        status_code=403,
        detail="Access forbidden",
        headers={"X-Error": "Custom error header"},
    )
```

## Custom Exception Classes

### Domain-Specific Exceptions

```python
# src/exceptions.py
from fastapi import HTTPException, status

class ItemNotFound(HTTPException):
    def __init__(self, item_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )

class DuplicateItem(HTTPException):
    def __init__(self, item_name: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item '{item_name}' already exists"
        )

class InsufficientPermissions(HTTPException):
    def __init__(self, action: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to {action}"
        )

# Usage in routes
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = await get_item_from_db(item_id)
    if not item:
        raise ItemNotFound(item_id)
    return item
```

### Module-Specific Exceptions

```python
# src/auth/exceptions.py
from fastapi import HTTPException, status

class AuthenticationError(HTTPException):
    """Base authentication exception."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class InvalidCredentials(AuthenticationError):
    def __init__(self):
        super().__init__("Invalid username or password")

class ExpiredToken(AuthenticationError):
    def __init__(self):
        super().__init__("Token has expired")

class InvalidToken(AuthenticationError):
    def __init__(self):
        super().__init__("Invalid token")

# src/posts/exceptions.py
from fastapi import HTTPException, status

class PostError(HTTPException):
    """Base post exception."""
    pass

class PostNotFound(PostError):
    def __init__(self, post_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )

class PostAccessDenied(PostError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't own this post"
        )
```

## Global Exception Handlers

### Custom Exception Handler

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle all HTTP exceptions with custom format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            }
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "type": "validation_error",
                "details": errors
            }
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected exceptions."""
    # Log the error
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "internal_error"
            }
        },
    )
```

### Custom Validation Error Response

```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return validation errors as plain text."""
    message = "Validation errors:\n"
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        message += f"  - {field}: {error['msg']}\n"

    return PlainTextResponse(message, status_code=400)
```

## Error Response Models

### Structured Error Response

```python
from pydantic import BaseModel
from typing import List, Optional, Any

class ErrorDetail(BaseModel):
    """Detailed error information."""
    field: str
    message: str
    type: str

class ErrorResponse(BaseModel):
    """Standard error response format."""
    code: int
    message: str
    type: str
    details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None
    timestamp: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": 404,
                    "message": "Resource not found",
                    "type": "not_found",
                    "request_id": "abc-123",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            ]
        }
    }

# Use in route documentation
@app.get(
    "/items/{item_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Item not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    }
)
async def get_item(item_id: int):
    pass
```

## Custom Error Middleware

### Error Tracking Middleware

```python
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import uuid

class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Log error with request ID
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Request {request_id} failed: {exc}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                }
            )

            # Return error with request ID
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "message": "Internal server error",
                        "request_id": request_id,
                        "timestamp": time.time()
                    }
                }
            )

app = FastAPI()
app.add_middleware(ErrorTrackingMiddleware)
```

## Validation Errors

### Enhanced Validation Error Handler

```python
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation error response."""
    # Parse errors into user-friendly format
    errors = {}
    for error in exc.errors():
        # Get field path (e.g., "body.user.email")
        field_path = ".".join(str(loc) for loc in error["loc"][1:])  # Skip "body"

        # Format error message
        msg = error["msg"]
        error_type = error["type"]

        # Customize messages
        if error_type == "value_error.missing":
            msg = "This field is required"
        elif error_type == "type_error.integer":
            msg = "Must be an integer"
        elif error_type == "value_error.email":
            msg = "Must be a valid email address"

        if field_path in errors:
            errors[field_path].append(msg)
        else:
            errors[field_path] = [msg]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Validation failed",
            "errors": errors
        }
    )
```

### Custom Validation with Context

```python
from fastapi import HTTPException, status
from pydantic import BaseModel, field_validator

class UserCreate(BaseModel):
    username: str
    email: str
    age: int

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if len(v) > 20:
            raise ValueError('Username must be at most 20 characters')
        return v

    @field_validator('age')
    @classmethod
    def age_valid(cls, v: int) -> int:
        if v < 13:
            raise ValueError('Must be at least 13 years old')
        if v > 120:
            raise ValueError('Age seems unrealistic')
        return v
```

## Database Errors

### Handle Database Exceptions

```python
from fastapi import FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError, DatabaseError
from asyncpg.exceptions import UniqueViolationError

app = FastAPI()

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request, exc: IntegrityError):
    """Handle database integrity errors."""
    # Parse the error to provide meaningful message
    error_message = str(exc.orig)

    if "unique constraint" in error_message.lower():
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": 409,
                    "message": "Resource already exists",
                    "type": "duplicate_error"
                }
            }
        )

    if "foreign key constraint" in error_message.lower():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": 400,
                    "message": "Referenced resource does not exist",
                    "type": "foreign_key_error"
                }
            }
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Database error",
                "type": "database_error"
            }
        }
    )

@app.post("/users")
async def create_user(user: UserCreate):
    try:
        return await create_user_in_db(user)
    except IntegrityError as e:
        # This will be caught by the handler above
        raise
```

## Custom Route Error Handler

### Per-Route Error Handling

```python
from fastapi import APIRouter, Request
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from typing import Callable

class CustomErrorRoute(APIRoute):
    """Custom route class with error handling."""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> JSONResponse:
            try:
                return await original_route_handler(request)
            except ValueError as exc:
                # Handle ValueError specifically
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": {
                            "code": 400,
                            "message": str(exc),
                            "type": "value_error"
                        }
                    }
                )
            except Exception as exc:
                # Log and return generic error
                import logging
                logging.error(f"Unhandled error in route: {exc}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "code": 500,
                            "message": "Internal server error",
                            "type": "internal_error"
                        }
                    }
                )

        return custom_route_handler

# Use custom route class
router = APIRouter(route_class=CustomErrorRoute)

@router.get("/items")
async def get_items():
    # Errors are automatically handled by CustomErrorRoute
    if some_condition:
        raise ValueError("Invalid condition")
    return items
```

## Logging Errors

### Structured Error Logging

```python
import logging
import json
from datetime import datetime
from fastapi import Request

logger = logging.getLogger(__name__)

class ErrorLogger:
    """Structured error logging."""

    @staticmethod
    def log_error(
        request: Request,
        exception: Exception,
        status_code: int,
        user_id: str | None = None
    ):
        """Log error with structured data."""
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "path": request.url.path,
            "method": request.method,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_id": user_id,
        }

        logger.error(
            f"API Error: {status_code} {type(exception).__name__}",
            extra={"error_data": json.dumps(error_data)},
            exc_info=True
        )

# Usage in exception handler
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    ErrorLogger.log_error(request, exc, 500)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
```

## Error Recovery

### Retry Logic

```python
import asyncio
from typing import TypeVar, Callable
from functools import wraps

T = TypeVar('T')

def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry function on error."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (attempt + 1))
                    else:
                        raise last_exception

            raise last_exception

        return wrapper
    return decorator

# Usage
@retry_on_error(max_retries=3, delay=1.0)
async def fetch_external_data(url: str):
    """Fetch data with automatic retry on failure."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

## Best Practices

✅ **Do:**

- Use appropriate HTTP status codes
- Provide clear error messages
- Create custom exceptions for domain errors
- Log errors with context (request ID, user ID, etc.)
- Use global exception handlers for consistency
- Return structured error responses
- Don't expose sensitive information in errors
- Document error responses in OpenAPI
- Test error scenarios

❌ **Don't:**

- Return generic "Error" messages
- Expose stack traces to clients
- Use wrong status codes (e.g., 500 for validation errors)
- Log sensitive data (passwords, tokens, etc.)
- Ignore errors silently
- Return different error formats from different endpoints
- Forget to handle database errors
- Leave unhandled exceptions

## Error Response Standards

### Recommended Error Structure

```python
{
    "error": {
        "code": 404,                    # HTTP status code
        "message": "User not found",    # Human-readable message
        "type": "not_found",            # Machine-readable error type
        "details": [                    # Optional detailed errors
            {
                "field": "user_id",
                "message": "User with id 123 does not exist",
                "type": "value_error"
            }
        ],
        "request_id": "abc-123",        # For tracking/debugging
        "timestamp": "2024-01-15T10:30:00Z",
        "documentation_url": "https://docs.example.com/errors/not-found"
    }
}
```

## Common HTTP Status Codes

| Code | Meaning               | When to Use                                |
| ---- | --------------------- | ------------------------------------------ |
| 400  | Bad Request           | Invalid request syntax or parameters       |
| 401  | Unauthorized          | Authentication required                    |
| 403  | Forbidden             | Authenticated but lacks permissions        |
| 404  | Not Found             | Resource doesn't exist                     |
| 409  | Conflict              | Duplicate resource or constraint violation |
| 422  | Unprocessable Entity  | Validation errors                          |
| 429  | Too Many Requests     | Rate limit exceeded                        |
| 500  | Internal Server Error | Unexpected server error                    |
| 502  | Bad Gateway           | Upstream service error                     |
| 503  | Service Unavailable   | Server overloaded or maintenance           |

## Summary

Effective error handling in FastAPI requires:

1. **Consistent error responses** across all endpoints
2. **Appropriate status codes** for different error types
3. **Clear error messages** that help users understand what went wrong
4. **Structured logging** for debugging and monitoring
5. **Security** - don't expose sensitive information
6. **Documentation** of error responses in OpenAPI
7. **Global handlers** for consistent error formatting
8. **Custom exceptions** for domain-specific errors

Well-handled errors improve user experience, simplify debugging, and make your API more professional.
