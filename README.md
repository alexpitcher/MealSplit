# MealSplit Backend

A FastAPI-based backend for MealSplit - an OCR-based grocery receipt splitting application.

## Overview

MealSplit helps households split grocery costs fairly by:
- Planning weekly meals with recipe ingredients
- Scanning grocery receipts with OCR
- Automatically matching receipt items to planned ingredients
- Calculating fair cost splits based on consumption
- Optionally syncing settlements to Splitwise

## Tech Stack

- **FastAPI** - Modern web framework for building APIs
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Primary database
- **Redis** - Caching and pub/sub messaging
- **Alembic** - Database migrations
- **Docker** - Containerized development environment

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Development Setup

1. **Clone and setup environment**:
   ```bash
   git clone <repository-url>
   cd MealSplit
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start services with Docker**:
   ```bash
   docker-compose up -d
   ```

3. **Run database migrations**:
   ```bash
   docker-compose --profile tools run migrate
   ```

4. **Access the API**:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - PostgreSQL: localhost:5432
   - Redis: localhost:6379

### Local Development (without Docker)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup database**:
   ```bash
   # Start PostgreSQL and Redis locally
   # Update DATABASE_URL and REDIS_URL in .env
   alembic upgrade head
   ```

3. **Run the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure

```
├── app/
│   ├── api/v1/          # API route handlers
│   ├── core/            # Core configuration and utilities
│   ├── models/          # SQLAlchemy database models
│   ├── schemas/         # Pydantic request/response models
│   ├── services/        # Business logic layer
│   └── workers/         # Background job handlers
├── alembic/             # Database migrations
├── tests/               # Test files
├── docker-compose.yml   # Development environment
├── Dockerfile          # Container configuration
└── requirements.txt    # Python dependencies
```

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /signup` - Register new user
- `POST /login` - User login
- `POST /refresh` - Refresh access token
- `GET /me` - Get current user info

### Households (`/api/v1/households`)
- `POST /` - Create household
- `GET /{household_id}` - Get household details
- `POST /{household_id}/join` - Join household

### Planning (`/api/v1/planning`)
- `GET /weeks` - Get planning weeks
- `POST /weeks/{week_id}/recipes` - Add recipe to week
- `GET /weeks/{week_id}/shopping-list` - Get shopping list

### Receipts (`/api/v1/receipts`)
- `POST /` - Upload receipt for OCR
- `GET /{receipt_id}` - Get receipt details
- `GET /weeks/{week_id}/matches/pending` - Get pending matches
- `POST /matches/{receipt_line_id}/confirm` - Confirm line match

### Settlements (`/api/v1/settlements`)
- `GET /weeks/{week_id}/settlement` - Get settlement summary
- `POST /weeks/{week_id}/close` - Close week settlements

### Splitwise (`/api/v1/splitwise`)
- `GET /oauth/start` - Start OAuth flow
- `GET /oauth/callback` - Handle OAuth callback
- `GET /me` - Get Splitwise user info

## Database Schema

### Core Tables
- `users` - User accounts and authentication
- `households` - Household groups
- `household_users` - Membership and default shares

### Planning Tables
- `planning_weeks` - Weekly meal planning periods
- `recipes` - Recipe definitions from Mealie
- `week_recipes` - Recipes planned for specific weeks
- `recipe_ingredients` - Ingredients required for recipes
- `shopping_items` - Consolidated shopping list items

### Receipt Tables
- `receipts` - Uploaded receipt metadata
- `receipt_lines` - Individual line items from OCR
- `line_matches` - Matches between receipt lines and ingredients

### Settlement Tables
- `settlements` - Final cost splits between users
- `splitwise_links` - OAuth tokens for Splitwise integration

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mealsplit

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=480

# External APIs
OPENAI_API_KEY=your-openai-key
SPLITWISE_CLIENT_ID=your-splitwise-client-id
SPLITWISE_CLIENT_SECRET=your-splitwise-secret

# File Storage
UPLOAD_DIR=/tmp/uploads
MAX_UPLOAD_SIZE=10485760
```

## Development

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Downgrade one revision
alembic downgrade -1
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

### Code Quality

```bash
# Format code
black app/

# Lint code
ruff app/

# Type checking
mypy app/
```

## Production Deployment

1. **Build production image**:
   ```bash
   docker build --target production -t mealsplit-backend .
   ```

2. **Set production environment variables**:
   - Use strong SECRET_KEY
   - Configure production database
   - Set ENVIRONMENT=production
   - Configure external API keys

3. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Deploy with proper reverse proxy and SSL**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

[Your chosen license]