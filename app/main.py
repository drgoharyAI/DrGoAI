"""DrGoAi Pre-Authorization System - Main Application"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import sys
from pathlib import Path

try:
    from app.config.settings import settings
except:
    class Settings:
        APP_NAME = "DrGoAi Pre-Authorization System"
        VERSION = "3.0.0"
        DEBUG = True
        HOST = "0.0.0.0"
        PORT = 8000
        API_V1_PREFIX = "/api/v1"
        ALLOWED_ORIGINS = ["*"]
        LOG_LEVEL = "INFO"
        LOG_FILE = "logs/app.log"
    settings = Settings()

from app.api import endpoints, category_endpoints, fhir_testing, rag_endpoints, fhir_testing_enhanced, management_endpoints, test_endpoints

log_path = Path("logs")
log_path.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stdout, level=settings.LOG_LEVEL)
logger.add(f"{settings.LOG_FILE}", rotation="500 MB", retention="30 days", level=settings.LOG_LEVEL)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered pre-authorization with OCR",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass

app.include_router(endpoints.router, prefix=settings.API_V1_PREFIX, tags=["Adjudication"])
app.include_router(category_endpoints.router, prefix=f"{settings.API_V1_PREFIX}/categories", tags=["Categories"])
app.include_router(fhir_testing.router, prefix=settings.API_V1_PREFIX, tags=["FHIR Testing"])
app.include_router(fhir_testing_enhanced.router, prefix=settings.API_V1_PREFIX, tags=["FHIR Enhanced"])
app.include_router(rag_endpoints.router, prefix=settings.API_V1_PREFIX, tags=["RAG"])
app.include_router(management_endpoints.router, prefix=settings.API_V1_PREFIX, tags=["Management"])
app.include_router(test_endpoints.router, prefix=settings.API_V1_PREFIX, tags=["Testing"])

@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        return FileResponse("templates/index.html")
    except:
        return HTMLResponse(f"""<!DOCTYPE html><html><head><title>{settings.APP_NAME}</title><style>
body{{font-family:Arial;margin:40px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff}}
.container{{background:#fff;color:#333;padding:40px;border-radius:15px;max-width:800px;margin:0 auto;box-shadow:0 10px 30px rgba(0,0,0,0.3)}}
h1{{color:#667eea}}.link{{display:block;padding:15px;margin:10px 0;background:#667eea;color:#fff;text-decoration:none;border-radius:8px;text-align:center}}
.link:hover{{background:#5568d3}}</style></head><body><div class="container"><h1>🏥 {settings.APP_NAME}</h1>
<p>Version {settings.VERSION}</p><h2>Quick Links</h2>
<a href="/fhir-testing" class="link">🧪 FHIR Testing</a>
<a href="/docs" class="link">📚 API Docs</a>
<a href="{settings.API_V1_PREFIX}/health" class="link">❤️ Health</a></div></body></html>""")

@app.get("/fhir-testing", response_class=HTMLResponse)
async def fhir_testing_page():
    return FileResponse("templates/fhir-testing.html")

@app.get(f"{settings.API_V1_PREFIX}/health")
async def health_check():
    return {"status":"healthy","version":settings.VERSION,"features":{"fhir_parsing":True,"ocr_support":True,"ai_layers":True}}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error: {str(exc)}")
    return JSONResponse(status_code=500, content={"error":"Internal Server Error","detail":str(exc)})

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    try:
        from app.db.database import init_db
        from app.db.seed_data import seed_initial_data
        init_db()
        seed_initial_data()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.warning(f"Database: {e}")
    logger.info(f"Access: http://{settings.HOST}:{settings.PORT}/fhir-testing")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

@app.get("/medical-rules", response_class=HTMLResponse)
async def medical_rules_page():
    try:
        return FileResponse("templates/medical-rules.html")
    except:
        return HTMLResponse("<h1>Medical Rules</h1><p>Template not found</p>")

@app.get("/hd-conditions", response_class=HTMLResponse)
async def hd_conditions_page():
    try:
        return FileResponse("templates/hd-conditions.html")
    except:
        return HTMLResponse("<h1>Health Conditions</h1><p>Template not found</p>")

@app.get("/fraud-rules", response_class=HTMLResponse)
async def fraud_rules_page():
    try:
        return FileResponse("templates/fraud-rules.html")
    except:
        return HTMLResponse("<h1>Fraud Rules</h1><p>Template not found</p>")

@app.get("/risk-parameters", response_class=HTMLResponse)
async def risk_parameters_page():
    try:
        return FileResponse("templates/risk-parameters.html")
    except:
        return HTMLResponse("<h1>Risk Parameters</h1><p>Template not found</p>")

@app.get("/rag-database", response_class=HTMLResponse)
async def rag_database_page():
    try:
        return FileResponse("templates/rag-database.html")
    except:
        return HTMLResponse("<h1>RAG Database</h1><p>Template not found</p>")

@app.get("/llm-models", response_class=HTMLResponse)
async def llm_models_page():
    try:
        return FileResponse("templates/llm-models.html")
    except:
        return HTMLResponse("<h1>LLM Models</h1><p>Template not found</p>")

@app.get("/file-management", response_class=HTMLResponse)
async def file_management_page():
    try:
        return FileResponse("templates/file-management.html")
    except:
        return HTMLResponse("<h1>File Management</h1><p>Template not found</p>")
