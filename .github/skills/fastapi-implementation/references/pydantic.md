# Pydantic Validation and Schemas

## Overview

Pydantic is FastAPI's validation powerhouse. Use it extensively for request/response validation, configuration, and data transformation.

## Core Principle

**Validate early, validate often.** Let Pydantic catch invalid data before it reaches your business logic.

## Basic Schema Definition

### Request/Response Models

```python
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    full_name: str | None = None

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)  # For ORM models

class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = None
    full_name: str | None = None
```

## Built-in Validators

### Use Pydantic's Rich Validation

```python
from pydantic import (
    BaseModel,
    EmailStr,           # Email validation
    HttpUrl,            # URL validation
    IPvAnyAddress,      # IP address validation
    Field,              # Field constraints
    constr,             # Constrained string
    conint,             # Constrained integer
    confloat,           # Constrained float
    conlist,            # Constrained list
    validator,
    field_validator,
)
from typing import Annotated

class UserProfile(BaseModel):
    # Email validation
    email: EmailStr

    # String constraints
    username: Annotated[str, Field(min_length=3, max_length=20, pattern="^[a-zA-Z0-9_]+$")]

    # Alternative using constr (older style)
    bio: constr(max_length=500) | None = None

    # Integer constraints
    age: Annotated[int, Field(ge=13, le=120)]  # 13 <= age <= 120

    # Float constraints
    rating: Annotated[float, Field(ge=0.0, le=5.0)]

    # URL validation
    website: HttpUrl | None = None

    # List constraints
    tags: Annotated[list[str], Field(min_length=1, max_length=10)]

    # Enum validation
    status: Literal["active", "inactive", "banned"]
```

### Common Field Constraints

```python
from pydantic import BaseModel, Field
from typing import Annotated

class Product(BaseModel):
    # Strings
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=2000)]
    sku: Annotated[str, Field(pattern=r"^[A-Z]{3}-\d{6}$")]  # e.g., ABC-123456

    # Numbers
    price: Annotated[float, Field(gt=0, le=1_000_000)]  # 0 < price <= 1,000,000
    quantity: Annotated[int, Field(ge=0)]  # quantity >= 0
    discount: Annotated[float, Field(ge=0.0, le=100.0)]  # 0-100%

    # Lists
    images: Annotated[list[str], Field(min_length=1, max_length=5)]
    categories: Annotated[list[str], Field(min_length=1)]
```

**Field constraint parameters:**

- `gt` (greater than), `ge` (greater or equal)
- `lt` (less than), `le` (less or equal)
- `min_length`, `max_length`
- `pattern` (regex)
- `multiple_of` (for numbers)

## Custom Validators

### Field Validators

```python
from pydantic import BaseModel, field_validator, ValidationError

class Post(BaseModel):
    title: str
    content: str
    tags: list[str]

    @field_validator('title')
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        return v.strip().title()  # Capitalize

    @field_validator('tags')
    @classmethod
    def tags_must_be_unique(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError('Tags must be unique')
        return [tag.lower() for tag in v]  # Normalize

    @field_validator('content')
    @classmethod
    def content_must_have_minimum_words(cls, v: str) -> str:
        word_count = len(v.split())
        if word_count < 10:
            raise ValueError(f'Content must have at least 10 words (got {word_count})')
        return v
```

### Model Validators

For validation that needs multiple fields:

```python
from pydantic import BaseModel, model_validator
from datetime import datetime

class Event(BaseModel):
    title: str
    start_date: datetime
    end_date: datetime

    @model_validator(mode='after')
    def check_dates(self) -> 'Event':
        if self.end_date <= self.start_date:
            raise ValueError('end_date must be after start_date')
        return self

    @model_validator(mode='after')
    def check_duration(self) -> 'Event':
        duration = (self.end_date - self.start_date).days
        if duration > 365:
            raise ValueError('Event cannot last more than a year')
        return self
```

### Validators with Mode

```python
from pydantic import field_validator

class User(BaseModel):
    email: str

    # mode='before': Runs before Pydantic's type validation
    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v):
        if isinstance(v, str):
            return v.lower().strip()
        return v

    # mode='after': Runs after Pydantic's type validation (default)
    @field_validator('email', mode='after')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v.endswith('@company.com'):
            raise ValueError('Must be a company email')
        return v
```

## Custom Base Model

Create a global base model for consistent behavior:

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from zoneinfo import ZoneInfo

def serialize_datetime(dt: datetime) -> str:
    """Serialize datetime to ISO format with explicit timezone."""
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.isoformat()

class CustomBaseModel(BaseModel):
    """Base model with custom configuration for all schemas."""

    model_config = ConfigDict(
        # Serialization
        json_encoders={
            datetime: serialize_datetime,
        },

        # Allow populating by field name or alias
        populate_by_name=True,

        # Validate on assignment
        validate_assignment=True,

        # Allow getting attributes from ORM models
        from_attributes=True,

        # Strict type checking
        strict=False,  # Set True for stricter validation

        # Remove extra fields not defined in model
        extra='forbid',  # Or 'allow' or 'ignore'

        # Use enum values instead of enum objects
        use_enum_values=True,
    )

    def dict_serializable(self) -> dict:
        """Return dict with only JSON-serializable values."""
        return self.model_dump(mode='json')

# All schemas inherit from this
class UserResponse(CustomBaseModel):
    id: int
    email: str
    created_at: datetime
```

### Model Config Options

```python
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        # Validation
        validate_assignment=True,        # Validate when setting attributes
        validate_default=True,           # Validate default values
        strict=True,                     # Strict type checking

        # Extra fields
        extra='forbid',                  # Forbid extra fields (or 'allow', 'ignore')

        # Serialization
        use_enum_values=True,            # Serialize enums as values
        populate_by_name=True,           # Allow field name or alias
        from_attributes=True,            # Load from ORM objects

        # JSON schema
        json_schema_extra={               # Extra info for OpenAPI
            "example": {
                "field": "value"
            }
        },

        # Misc
        arbitrary_types_allowed=False,   # Allow non-Pydantic types
        str_strip_whitespace=True,       # Strip whitespace from strings
        str_to_lower=False,              # Convert strings to lowercase
        str_to_upper=False,              # Convert strings to uppercase
    )
```

## Pydantic BaseSettings

Split configuration by domain:

### Global Settings

```python
# src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    """Global application settings."""

    # App
    APP_NAME: str = "My FastAPI App"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str | None = None

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore unknown env vars
    )

settings = Settings()
```

### Domain-Specific Settings

```python
# src/auth/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class AuthConfig(BaseSettings):
    """Authentication domain settings."""

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True

    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",  # All vars start with AUTH_
        env_file=".env",
    )

auth_config = AuthConfig()

# Usage
# In .env file:
# AUTH_JWT_SECRET_KEY=secret
# AUTH_MAX_LOGIN_ATTEMPTS=3
```

### Environment Variables Priority

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    api_key: str

    model_config = SettingsConfigDict(
        # Priority (highest to lowest):
        # 1. Environment variables
        # 2. .env file
        # 3. Default values
        env_file=".env",
        env_file_encoding="utf-8",

        # Support multiple .env files
        # env_file=(".env", ".env.local", ".env.production"),

        # Nested environment variables
        env_nested_delimiter="__",  # API__KEY -> api.key
    )
```

## Advanced Validation Patterns

### Dependent Fields

```python
from pydantic import BaseModel, model_validator

class UserRegistration(BaseModel):
    password: str
    password_confirm: str

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserRegistration':
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self
```

### Conditional Validation

```python
from pydantic import BaseModel, field_validator
from typing import Literal

class Payment(BaseModel):
    method: Literal["credit_card", "bank_transfer", "paypal"]
    card_number: str | None = None
    bank_account: str | None = None
    paypal_email: str | None = None

    @model_validator(mode='after')
    def check_payment_details(self) -> 'Payment':
        if self.method == "credit_card" and not self.card_number:
            raise ValueError('card_number required for credit card payments')
        if self.method == "bank_transfer" and not self.bank_account:
            raise ValueError('bank_account required for bank transfers')
        if self.method == "paypal" and not self.paypal_email:
            raise ValueError('paypal_email required for PayPal payments')
        return self
```

### List Validation

```python
from pydantic import BaseModel, field_validator

class BulkUserCreate(BaseModel):
    users: list[UserCreate]

    @field_validator('users')
    @classmethod
    def check_unique_emails(cls, v: list[UserCreate]) -> list[UserCreate]:
        emails = [user.email for user in v]
        if len(emails) != len(set(emails)):
            raise ValueError('Duplicate emails in user list')
        return v

    @field_validator('users')
    @classmethod
    def check_max_batch_size(cls, v: list[UserCreate]) -> list[UserCreate]:
        if len(v) > 100:
            raise ValueError('Cannot create more than 100 users at once')
        return v
```

## Serialization Patterns

### Excluding Fields

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    username: str
    email: str
    password_hash: str

    def to_public(self) -> dict:
        """Serialize without sensitive fields."""
        return self.model_dump(exclude={'password_hash'})

# In route
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await get_user_by_id(user_id)
    return user.to_public()
```

### Multiple Representation Models

```python
class UserInDB(BaseModel):
    """Full user data from database."""
    id: int
    username: str
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime

class UserPublic(BaseModel):
    """Public user profile."""
    id: int
    username: str
    created_at: datetime

class UserPrivate(BaseModel):
    """Private user data (for the user themselves)."""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

# In service
def to_public(user: UserInDB) -> UserPublic:
    return UserPublic(**user.model_dump())

def to_private(user: UserInDB) -> UserPrivate:
    return UserPrivate(**user.model_dump())
```

### Response Model with ORM

```python
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase

# ORM Model
class User(DeclarativeBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)
    created_at = Column(DateTime)

# Pydantic Model
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Usage
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    user = await db.get(User, user_id)  # Returns ORM object
    return user  # FastAPI converts using from_attributes=True
```

## Common Patterns

### Partial Updates

```python
from pydantic import BaseModel

class UserUpdate(BaseModel):
    """All fields optional for partial updates."""
    username: str | None = None
    email: EmailStr | None = None
    full_name: str | None = None

    def update_dict(self, exclude_unset: bool = True) -> dict:
        """Get only the fields that were actually set."""
        return self.model_dump(exclude_unset=exclude_unset)

# Usage
@router.patch("/users/{user_id}")
async def update_user(user_id: int, update: UserUpdate):
    # Only updates fields that were provided
    update_data = update.update_dict(exclude_unset=True)
    await db.update(User, user_id, update_data)
```

### Aliasing

```python
from pydantic import BaseModel, Field

class UserSchema(BaseModel):
    """Map API fields to different internal names."""
    user_id: int = Field(alias="id")
    user_name: str = Field(alias="username")

    model_config = ConfigDict(populate_by_name=True)

# Accepts both "id" and "user_id" in input
```

### Generic Response Models

```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    message: str | None = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size

# Usage
@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(page: int = 1, page_size: int = 20):
    users, total = await get_users(page, page_size)
    return PaginatedResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size
    )
```

## Error Handling

### Pydantic Validation Errors

FastAPI automatically converts Pydantic validation errors to HTTP 422 responses:

```python
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Custom validation error response."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": errors,
        }
    )
```

## Best Practices

✅ **Do:**

- Use Pydantic's built-in validators when possible
- Create custom base models for consistent behavior
- Split BaseSettings by domain
- Use `response_model` in routes
- Validate at the edge (in schemas, not business logic)
- Use meaningful error messages in validators
- Leverage type hints for automatic validation

❌ **Don't:**

- Validate manually what Pydantic can do
- Put business logic in validators (keep them pure)
- Have one giant BaseSettings class
- Ignore validation errors
- Over-complicate validators
- Forget to use `ConfigDict` for ORM integration

## Performance Tips

1. **Use `model_dump()` instead of `dict()`**

   ```python
   user.model_dump()  # Fast ✅
   dict(user)         # Slower ❌
   ```

2. **Exclude unset for partial updates**

   ```python
   update.model_dump(exclude_unset=True)  # Only changed fields
   ```

3. **Use `model_validate()` for trusted data**

   ```python
   User.model_validate(db_row)  # Faster than User(**db_row)
   ```

4. **Defer validation when possible**
   ```python
   model_config = ConfigDict(validate_assignment=False)  # Only validate on init
   ```

## Summary

Pydantic is your first line of defense against bad data. Use it extensively for:

- Request/response validation
- Configuration management
- Data transformation
- Type safety
- Automatic documentation

Remember: **The more you validate with Pydantic, the less defensive code you need elsewhere.**
