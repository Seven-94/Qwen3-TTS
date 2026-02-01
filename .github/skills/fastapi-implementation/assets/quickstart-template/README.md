# FastAPI Quickstart Template

This template provides a minimal, production-ready FastAPI application structure following best practices.

## Structure

```
quickstart-template/
├── src/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration
│   ├── database.py          # Database setup
│   ├── exceptions.py        # Global exceptions
│   └── auth/                # Example domain module
│       ├── __init__.py
│       ├── router.py
│       ├── schemas.py
│       ├── models.py
│       ├── service.py
│       └── dependencies.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── auth/
│       └── test_router.py
├── alembic/
│   └── versions/
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Quick Start

1. **Copy this template:**

   ```bash
   cp -r .github/skills/fastapi-implementation/assets/quickstart-template my-api
   cd my-api
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   # or with poetry:
   poetry install
   ```

3. **Configure environment:**

   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run migrations:**

   ```bash
   alembic upgrade head
   ```

5. **Start development server:**

   ```bash
   uvicorn src.main:app --reload
   ```

6. **Access docs:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Features

- ✅ Async-first architecture
- ✅ Domain-based structure
- ✅ Database with SQLAlchemy (async)
- ✅ Migrations with Alembic
- ✅ Pydantic validation
- ✅ JWT authentication example
- ✅ Dependency injection
- ✅ Error handling
- ✅ Testing setup
- ✅ Environment configuration
- ✅ API documentation

## Customization

1. **Add new domain:** Create a new folder in `src/` with router, schemas, models, etc.
2. **Configure database:** Update `DATABASE_URL` in `.env`
3. **Add authentication:** Modify `src/auth/` to fit your needs
4. **Customize docs:** Update `title`, `description` in `src/main.py`

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Production Deployment

1. Set `ENVIRONMENT=production` in `.env`
2. Use proper secret keys
3. Configure CORS origins
4. Set up logging
5. Use production database
6. Deploy with Docker or cloud platform

See individual files for detailed implementation.
