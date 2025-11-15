# DrGoAi Production Deployment Guide

## Quick Start

### Development Mode
```bash
chmod +x start_dev.sh
./start_dev.sh
```

### Production Mode (Docker)
```bash
cp .env.example .env
# Edit .env with your configuration
docker-compose up -d
```

### Production Mode (Direct)
```bash
chmod +x start_production.sh
./start_production.sh
```

## Configuration

1. Copy `.env.example` to `.env`
2. Update the following in `.env`:
   - `SECRET_KEY`: Random string for JWT signing
   - `GOOGLE_API_KEY`: Your Gemini API key
   - `ALLOWED_ORIGINS`: Your frontend URLs
   - `DATABASE_URL`: Your database connection
   - `DEBUG`: Set to false for production

## Database Setup

```bash
# Automatic (on startup)
python -c "from app.db.database import init_db; init_db()"

# Manual migrations
alembic upgrade head
```

## Health Check

```bash
curl http://localhost:8000/api/v1/health
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Security Checklist

- [ ] Change SECRET_KEY in .env
- [ ] Set DEBUG=false
- [ ] Configure ALLOWED_ORIGINS
- [ ] Set up HTTPS/SSL
- [ ] Configure firewall rules
- [ ] Set up database backups
- [ ] Enable audit logging
- [ ] Configure rate limiting
- [ ] Set up monitoring/alerting
- [ ] Review security headers

## Monitoring

Logs are stored in `logs/` directory:
- `app.log`: Application logs
- `access.log`: HTTP access logs
- `error.log`: Error logs

## Troubleshooting

If the application fails to start:
1. Check logs in `logs/` directory
2. Verify `.env` configuration
3. Ensure database file is writable
4. Check Python and dependencies versions
