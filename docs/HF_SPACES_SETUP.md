# DrGoAi - HuggingFace Spaces Setup Guide

## Quick Deploy to HF Spaces

### Step 1: Create New Space
1. Go to https://huggingface.co/new-space
2. Select **FastAPI** as Space type
3. Name: `drgai-insurance-preauth`
4. Visibility: Public or Private

### Step 2: Upload Files
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/drgai-insurance-preauth
cd drgai-insurance-preauth

# Copy all DrGoAi files
cp -r ../DrGoAi/* .
git add .
git commit -m "Initial DrGoAi deployment"
git push
```

### Step 3: Configure Requirements
- Create/update `requirements.txt` (use `requirements-hf.txt` as base)
- Add only needed dependencies (HF Spaces has limited disk)

### Step 4: Set Startup
The Space will automatically detect and run `app.py` or use `uvicorn app.main:app`

HF automatically handles:
- ✅ Port (uses 7860 by default)
- ✅ Host (0.0.0.0)
- ✅ CORS (enabled for HF iframe)
- ✅ Static files (/static/* from static/ folder)

---

## Environment Variables (in HF Spaces)

Set in Space Settings → Environment Variables:

```
# Optional - API keys for LLM services
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Optional - Configuration
DEBUG=false
LOG_LEVEL=INFO
```

---

## HF Spaces Compatible Features

✅ Working:
- Dashboard with real data
- Medical Rules management
- Fraud Rules management  
- Health Conditions
- Risk Parameters
- LLM Models configuration
- System status monitoring
- RAG database operations
- FHIR testing interface

✅ API Endpoints:
- All management endpoints (`/api/v1/management/*`)
- RAG endpoints (`/api/v1/rag/*`)
- FHIR endpoints (`/api/v1/fhir/*`)

---

## Key Differences in HF Spaces

### 1. File Paths
```javascript
// Automatically handles relative paths
api.get('/medical-rules')
// Works in: http://localhost:7860 AND HF Spaces iframe
```

### 2. CORS Headers
- HF automatically adds CORS headers
- No configuration needed
- `credentials: 'include'` works

### 3. Static Files
- Place in `static/` folder
- Automatically served from `/static/*`
- CSS, JS, fonts all work

### 4. API Responses
- Keep response format consistent
- Return data directly (not wrapped unnecessarily)
- Use `timestamp: datetime.utcnow().isoformat()`

---

## Troubleshooting HF Spaces

### Issue: CORS Errors
**Solution:** Already handled by HF, use relative paths

### Issue: 404 on static files
**Solution:** Ensure files in `static/` folder (CSS, JS, etc.)

### Issue: Port binding error
**Solution:** HF handles PORT env variable automatically

### Issue: Module import errors
**Solution:** 
- Check `requirements.txt` has all dependencies
- Must be installed before Space starts

### Issue: Long startup time
**Solution:**
- First start takes time (docker build)
- Subsequent starts are instant
- Check logs for import errors

---

## Performance Tips for HF Spaces

1. **Minimize Dependencies**
   - Only include required packages
   - Current: ~200MB with all deps

2. **Cache Data**
   - Medical rules/conditions cached on startup
   - RAG database cached in memory

3. **Lazy Loading**
   - Frontend loads data on demand
   - No unnecessary API calls on page load

4. **Optimize API Responses**
   - Return minimal data needed
   - Use pagination for large lists

---

## Monitoring & Logs

In HF Spaces, view logs:
1. Open Space page
2. Click "Logs" button (top right)
3. See real-time application logs

Logs show:
- API requests: `[API] GET /api/v1/management/system-status`
- Errors: `[API ERROR] 500: ...`
- System startup: `Starting DrGoAi...`

---

## Customization for KSA Healthcare

### Medical Rules (Saudi Arabia Specific)
Edit in Dashboard or API:
- Add KSA-specific coverage rules
- Configure for NPHIES requirements
- Set fraud detection parameters

### Health Declaration
- Configure HD conditions specific to KSA policy
- Set waiting periods per GOSI requirements
- Define pre-existing condition rules

### LLM Integration
- Configure Arabic language support
- Add medical terminology translations
- Set clinical guideline preferences

---

## Example: Deploy to HF Spaces

```bash
# 1. Create repo structure
mkdir drgai-hf
cd drgai-hf

# 2. Copy DrGoAi files
cp -r ../DrGoAi/* .

# 3. Create .gitignore
echo "__pycache__/
*.pyc
.env
logs/
data/chroma/
.DS_Store" > .gitignore

# 4. Initialize git (HF will provide repo)
git init
git remote add origin https://huggingface.co/spaces/USERNAME/drgai
git add .
git commit -m "Initial DrGoAi setup for KSA health insurance"
git push -u origin main

# 5. Space automatically builds and deploys
# Monitor at: https://huggingface.co/spaces/USERNAME/drgai
```

---

## Features Ready for KSA Market

✅ NPHIES Compliance
✅ Health Declaration Management
✅ Fraud Detection
✅ Medical Necessity Validation
✅ Risk Assessment
✅ Multi-layer decision making
✅ Audit Trail
✅ Arabic-ready UI (add translation)

---

**Version:** DrGoAi HF Spaces Ready v1.0
**Last Updated:** November 2025
**Status:** ✅ Production Ready for HF Spaces
