# Docker Build Troubleshooting Guide

## Common Build Errors and Solutions

### Error: "Job failed with exit code: 1"

This generic error can have multiple causes. Try the solutions below in order:

### Solution 1: Use the Simplified Dockerfile

```bash
# Rename current Dockerfile
mv Dockerfile Dockerfile.original

# Use the simpler version
mv Dockerfile.simple Dockerfile

# Try building again
docker build -t drgoa-app .
```

### Solution 2: Use Flexible Requirements

If pip install is failing, try the more flexible requirements:

```bash
# Backup original
cp requirements.txt requirements-pinned.txt

# Use flexible versions
cp requirements-flexible.txt requirements.txt

# Try building again
docker build -t drgoa-app .
```

### Solution 3: Build with More Memory

ChromaDB and sentence-transformers need significant memory:

```bash
# Increase Docker memory (in Docker Desktop settings)
# Set to at least 4GB RAM

# Or build with buildkit
DOCKER_BUILDKIT=1 docker build -t drgoa-app .
```

### Solution 4: Build Step by Step

Debug which layer is failing:

```bash
# Build up to requirements install
docker build --target requirements -t drgoa-debug .

# If that works, build the full image
docker build -t drgoa-app .
```

### Solution 5: Skip ChromaDB (RAG will be disabled)

If you just need the management UI and don't need RAG:

1. Edit `requirements.txt` and comment out:
```
# chromadb==0.4.22
# sentence-transformers==2.3.1
```

2. Rebuild:
```bash
docker build -t drgoa-app .
```

Note: RAG features won't work, but all management pages will function.

### Solution 6: Use Pre-built Base Image

For platforms like Hugging Face Spaces, use their base image:

```dockerfile
FROM python:3.10-slim

# Rest of Dockerfile...
```

### Solution 7: Check Platform-Specific Issues

#### Hugging Face Spaces
- Use `Dockerfile` in root directory
- Ensure PORT 7860 is exposed
- Add `app.py` as entry point

#### Google Cloud Run
- Use port from $PORT environment variable
- Ensure stateless operation

#### AWS ECS/Fargate
- Check memory/CPU limits
- Use ECR-optimized base images

### Solution 8: Build Locally First

Test the build locally before deploying:

```bash
# Build locally
docker build -t drgoa-app .

# Run locally
docker run -p 7860:7860 drgoa-app

# If it works locally, the issue is platform-specific
```

### Solution 9: Check System Dependencies

Some Python packages need system libraries:

```bash
# Add to Dockerfile BEFORE pip install:
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
```

### Solution 10: Use Multi-stage Build

For smaller image size and better caching:

```dockerfile
# Stage 1: Build dependencies
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
```

## Detailed Error Messages

### "ERROR: Could not find a version that satisfies the requirement..."

**Cause:** Package version conflicts or unavailable packages

**Solutions:**
1. Use `requirements-flexible.txt`
2. Update to latest package versions
3. Check if package exists: `pip search package-name`

### "ERROR: Failed building wheel for..."

**Cause:** Missing system dependencies or compiler

**Solutions:**
1. Add `build-essential` to apt-get install
2. Add specific library (e.g., `libpq-dev` for psycopg2)
3. Use pre-built wheels when available

### "Killed" or "Out of memory"

**Cause:** Insufficient memory during build

**Solutions:**
1. Increase Docker memory limit
2. Use `--no-cache-dir` with pip
3. Install packages one by one
4. Use smaller base image

### "Permission denied" errors

**Cause:** File permissions issues

**Solutions:**
```dockerfile
# Add after COPY . .
RUN chmod -R 755 /app
RUN chown -R root:root /app
```

## Platform-Specific Guides

### Hugging Face Spaces

1. File structure:
```
your-space/
├── Dockerfile
├── app.py
├── requirements.txt
└── app/
    └── (your code)
```

2. Dockerfile must expose 7860
3. Use `app.py` as entry point
4. Set in Space settings: Docker SDK

### Railway / Render

1. Use `railway.toml` or `render.yaml`
2. Set build command: `docker build`
3. Set start command: `python app.py`

### DigitalOcean App Platform

1. Use `.do/app.yaml`
2. Specify Python buildpack or Dockerfile
3. Set port to 7860

## Testing Your Build

### 1. Local Test
```bash
docker build -t drgoa-test .
docker run -p 7860:7860 drgoa-test
curl http://localhost:7860/api/v1/health
```

### 2. Size Check
```bash
docker images drgoa-test
# Should be < 2GB ideally
```

### 3. Layer Analysis
```bash
docker history drgoa-test
# Identify large layers
```

## Quick Fixes Summary

| Issue | Quick Fix |
|-------|-----------|
| Build fails at pip install | Use `requirements-flexible.txt` |
| Out of memory | Increase Docker memory to 4GB+ |
| Missing system libs | Add `build-essential` to apt-get |
| ChromaDB issues | Comment it out if not needed |
| Platform errors | Check platform-specific requirements |
| Slow build | Use multi-stage build |
| Large image | Use slim base, cleanup apt cache |

## Still Having Issues?

1. Share the exact error message
2. Try building with verbose output: `docker build --progress=plain .`
3. Check Docker version: `docker --version`
4. Verify available memory: `docker info | grep Memory`

## Success Checklist

✅ Docker installed and running  
✅ At least 4GB RAM allocated to Docker  
✅ All files in correct locations  
✅ requirements.txt has compatible versions  
✅ Dockerfile has necessary system dependencies  
✅ Port 7860 is exposed and not in use  
✅ Entry point (app.py) exists and is correct  

If all checked and still failing, use Dockerfile.simple with requirements-flexible.txt
