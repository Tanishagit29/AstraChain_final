from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.middleware.cors import setup_cors
from app.middleware.error_handler import setup_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.database.session import SessionLocal, get_db
from app.database.init_db import init_db
from app.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing TransitOps Backend Application...")
    db = SessionLocal()
    try:
        init_db(db)
        logger.info("Database schemas initialized and seed data verified.")
    finally:
        db.close()
    yield
    logger.info("Shutting down TransitOps Backend Application.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic AI Supply Chain Intelligence & Demand Forecasting Enterprise Backend.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Setup Middlewares & Exception Handlers
setup_cors(app)
app.add_middleware(RequestLoggingMiddleware)
setup_exception_handlers(app)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"])
@app.get("/", tags=["Health Check"])
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
