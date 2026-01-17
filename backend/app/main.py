"""
Main FastAPI application entry point.
Initializes the app, middleware, and routes.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-agent system for learning American English",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """
    Run on application startup.
    Initialize connections, load data, etc.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # TODO: Initialize Azure services
    # TODO: Connect to Cosmos DB
    # TODO: Load initial data (vocabulary, grammar rules, sounds)

    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on application shutdown.
    Cleanup connections, save state, etc.
    """
    logger.info("Shutting down application...")

    # TODO: Close Azure connections
    # TODO: Close Cosmos DB connection
    # TODO: Cleanup resources

    logger.info("Application shutdown complete")


@app.get("/")
async def root():
    """Health check endpoint"""
    return JSONResponse(content={
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    })


@app.get("/health")
async def health_check():
    """
    Detailed health check endpoint.
    Check all service connections.
    """
    health_status = {
        "status": "healthy",
        "services": {
            "api": "up",
            # TODO: Check Azure OpenAI connection
            # TODO: Check Azure Speech Services connection
            # TODO: Check Cosmos DB connection
            # TODO: Check Redis connection (if enabled)
        }
    }

    return JSONResponse(content=health_status)


# Include routers
from app.api.v1.endpoints import vocabulary
from app.api.v1.endpoints import grammar
from app.api.v1.endpoints import pronunciation
from app.api.v1.endpoints import speaking
from app.api.v1.endpoints import progress
# TODO: Uncomment as endpoints are implemented
# from app.api.v1.endpoints import users, assessment
# app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["users"])
# app.include_router(assessment.router, prefix=f"{settings.API_V1_PREFIX}/assessment", tags=["assessment"])
app.include_router(vocabulary.router, prefix=f"{settings.API_V1_PREFIX}/vocabulary", tags=["vocabulary"])
app.include_router(grammar.router, prefix=f"{settings.API_V1_PREFIX}/grammar", tags=["grammar"])
app.include_router(pronunciation.router, prefix=f"{settings.API_V1_PREFIX}/pronunciation", tags=["pronunciation"])
app.include_router(speaking.router, prefix=f"{settings.API_V1_PREFIX}/speaking", tags=["speaking"])
app.include_router(progress.router, prefix=f"{settings.API_V1_PREFIX}/progress", tags=["progress"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
