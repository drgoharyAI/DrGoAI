# 🚀 Quick Start Guide - DrGoAi v3 Enhanced

## ⚡ 5-Minute Setup

### Step 1: Prerequisites Check
```bash
# Python version (3.10+ required)
python3 --version

# Install Tesseract OCR (for image processing)
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-ara
```

### Step 2: Install Dependencies
```bash
cd DrGoAiv3_Enhanced_v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### Step 3: Configuration
```bash
# Create .env file
cat > .env << 'EOF'
APP_NAME=DrGoAi Pre-Authorization System
VERSION=3.0.0-enhanced
DEBUG=true
HOST=0.0.0.0
PORT=8000
API_V1_PREFIX=/api/v1
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./drgoai.db
EOF
```

### Step 4: Run the Application
```bash
# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Access the Interface
Open your browser and navigate to:
- **Web Interface**: http://localhost:8000/fhir-testing
- **API Docs**: http://localhost:8000/docs

## 🎯 First Test

### Option 1: Web Interface
1. Go to http://localhost:8000/fhir-testing
2. Click "📋 Load Sample" button
3. Enable all AI layers
4. Click "🚀 Run AI Processing"
5. View results in the tabs

### Option 2: API Call
```bash
# Test the health endpoint
curl http://localhost:8000/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "3.0.0-enhanced",
#   "features": {
#     "fhir_parsing": true,
#     "ocr_support": true,
#     "ai_decision_layers": true,
#     "rag_system": true
#   }
# }
```

### Option 3: Test Script
```bash
# Run the comprehensive test
python3 test_enhanced_system.py

# Or test with your own JSON file
python3 test_enhanced_system.py /path/to/your/fhir_bundle.json
```

## 📋 Testing with Your FHIR Bundle

### Via Web Interface
1. Open http://localhost:8000/fhir-testing
2. **Drag & drop** your JSON file into the upload area
3. Or **paste** the JSON directly
4. Select which AI layers to enable:
   - ✅ Medical Rules Engine
   - ✅ Fraud Detection
   - ✅ Risk Assessment
   - ✅ Medical Necessity
   - ✅ Enable OCR for Attachments
5. Click "🚀 Run AI Processing"

### Via API
```python
import requests
import json

# Load your FHIR bundle
with open('your_bundle.json', 'r') as f:
    bundle_data = json.load(f)

# Process with all AI layers
response = requests.post(
    'http://localhost:8000/api/v1/fhir/process-with-ai',
    json={
        'bundle_data': bundle_data,
        'enabled_layers': {
            'medical_rules': True,
            'fraud_detection': True,
            'risk_assessment': True,
            'medical_necessity': True
        }
    }
)

result = response.json()
print(f"Decision: {result['results']['final_decision']['final_decision']}")
print(f"Confidence: {result['results']['final_decision']['confidence']}")
```

## 🔍 Understanding the Results

### Overview Tab
- **Final Decision**: APPROVED / REQUIRES_REVIEW / REJECTED
- **Confidence Score**: 0-100%
- **Total Amount**: Claim amount in SAR
- **Key Statistics**: Resources, items, attachments

### Claim Details Tab
- Line-by-line breakdown of services
- Individual decisions per item
- Approval/denial reasons

### Attachments & OCR Tab
- List of embedded PDFs/images
- Extracted text from each document
- OCR processing status

### AI Results Tab
- Medical Rules Engine results
- Fraud Detection findings
- Risk Assessment scores
- Medical Necessity validation

### Raw Data Tab
- Complete JSON response
- For integration and debugging

## 🎨 Customization

### Adjusting Decision Thresholds
Edit `app/services/decision_orchestrator.py`:
```python
# Fraud detection threshold
HIGH_RISK_THRESHOLD = 0.7  # Default

# Amount thresholds
HIGH_AMOUNT_THRESHOLD = 100000  # SAR
```

### Adding Custom Medical Rules
Edit `app/config/rules.yaml`:
```yaml
rules:
  - id: CUSTOM_RULE_001
    name: "Custom Service Check"
    condition: "service_code == 'ABC123'"
    action: "APPROVE"
    reason: "Pre-approved service"
```

### Customizing the UI
Edit `templates/fhir-testing.html`:
- Colors: Search for `#667eea` and `#764ba2`
- Layout: Modify the grid sections
- Features: Add/remove AI layers

## 📊 Performance Tips

### For Large Bundles
```python
# In app/config/settings.py
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB
OCR_TIMEOUT = 30  # seconds
```

### Database Optimization
```bash
# For production, use PostgreSQL
pip install psycopg2-binary
# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:pass@localhost/drgoai
```

### Caching Results
```python
# Add Redis for caching
pip install redis
# Configure in settings
REDIS_URL=redis://localhost:6379
```

## 🐛 Troubleshooting

### OCR Not Working
```bash
# Check Tesseract installation
tesseract --version
# Should show: tesseract 5.x.x

# Reinstall if needed
sudo apt-get install --reinstall tesseract-ocr

# Check Python packages
pip list | grep -i "pdf\|pillow\|pytesseract"
```

### Import Errors
```bash
# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Or in your IDE, mark 'app' as source root
```

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill it or use different port
uvicorn app.main:app --port 8001
```

### Module Not Found
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

## 📚 Next Steps

1. **Production Deployment**: See `docs/DEPLOYMENT.md`
2. **API Integration**: See `docs/API_GUIDE.md`
3. **Custom Rules**: See `docs/RULES_CONFIGURATION.md`
4. **Security**: See `docs/SECURITY.md`

## 💡 Pro Tips

- Use **Ctrl+Shift+F** in the web interface to format JSON
- Enable **all layers** for comprehensive analysis
- Check the **Raw Data** tab for debugging
- **Copy** the API endpoint URLs from the configuration panel
- View **attachment text** in the OCR tab before processing

## 🆘 Getting Help

- **Documentation**: http://localhost:8000/docs
- **Logs**: Check `logs/app.log`
- **Test Script**: `python3 test_enhanced_system.py`
- **Health Check**: http://localhost:8000/api/v1/health

---

**Ready to process your first authorization request?** 🚀

Go to: http://localhost:8000/fhir-testing
