# Delta 9 - Lead Generation Intelligence Platform

[![CI](https://github.com/yourusername/delta9/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/delta9/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade lead generation and buyer intelligence platform focused on the Kenyan market.

## 🚀 Features

- **🔍 Intelligent Search**: Multi-source lead discovery with intent scoring
- **🤖 Automated Agents**: Scheduled scraping with configurable parameters
- **📊 Kenya-Optimized**: Swahili/Sheng keyword detection and local market understanding
- **🔐 Secure**: JWT authentication, rate limiting, CORS protection
- **📈 Scalable**: Redis caching, Celery task queue, PostgreSQL database
- **🔔 Real-time**: WebSocket notifications, Telegram integration
- **📱 Modern API**: RESTful endpoints with automatic OpenAPI documentation

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI App                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │  Auth   │ │ Search  │ │ Agents  │ │ Telegram│          │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          │
└───────┼───────────┼───────────┼───────────┼────────────────┘
        │           │           │           │
        └───────────┴─────┬─────┴───────────┘
                          │
              ┌───────────┴───────────┐
              │     Services Layer     │
              │  (Business Logic)      │
              └───────────┬───────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────┴────┐      ┌────┴────┐      ┌────┴────┐
   │PostgreSQL│      │  Redis  │      │ Scrapers│
   │  (Data)  │      │ (Cache) │      │(Sources)│
   └─────────┘      └─────────┘      └─────────┘
```

## 🛠️ Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 14+ (or SQLite for development)
- Redis 7+

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/delta9.git
cd delta9
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -e ".[dev,scrapers,ai]"
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Start the application**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec api alembic upgrade head

# View logs
docker-compose logs -f api
```

### Production Deployment

```bash
# Build production image
docker build -t delta9:latest .

# Run with environment variables
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e SECRET_KEY=... \
  delta9:latest
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with markers
pytest -m "not slow"
```

## 📊 Project Structure

```
delta9/
├── app/
│   ├── api/              # API routes and dependencies
│   ├── core/             # Configuration, security, logging
│   ├── db/               # Database models and connection
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── scrapers/         # Web scrapers
│   └── utils/            # Utility functions
├── tests/                # Test suite
├── migrations/           # Alembic migrations
├── docker-compose.yml    # Docker services
├── Dockerfile            # Production image
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

## 🔒 Security

- **Authentication**: JWT tokens with access/refresh token pattern
- **Authorization**: Role-based access control
- **Rate Limiting**: Configurable per-endpoint limits
- **CORS**: Environment-based origin whitelist
- **Input Validation**: Pydantic schemas with strict validation
- **Password Hashing**: bcrypt with appropriate work factor

## 🔧 Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./delta9.db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing key | Required |
| `ENVIRONMENT` | dev/staging/production | `development` |
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |

See `.env.example` for complete configuration options.

## 📈 Monitoring

### Health Checks

- `GET /health` - Application health
- `GET /ready` - Readiness check (for K8s)
- `GET /api/info` - API information

### Logging

Structured JSON logging in production:

```json
{
  "event": "Request completed",
  "request_id": "abc-123",
  "method": "GET",
  "path": "/api/agents",
  "status_code": 200,
  "duration_ms": 45.2
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Format code with `black`
- Lint with `ruff`
- Type check with `mypy`
- Follow PEP 8 guidelines

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Celery](https://docs.celeryproject.org/) - Task queue
- [Playwright](https://playwright.dev/) - Browser automation

---

Built with ❤️ for the Kenyan market.
