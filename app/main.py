"""
RenderCV Backend - Main FastAPI Application

A high-performance API for generating professional resumes using RenderCV.
Supports PDF generation with multiple themes.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from app.api.routes import router
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Check RenderCV availability
    try:
        import rendercv
        if hasattr(rendercv, 'create_a_pdf_from_a_python_dictionary'):
            logger.info(f"RenderCV v{rendercv.__version__} is available and ready")
        else:
            logger.warning("RenderCV is installed but API may have changed")
    except ImportError as e:
        logger.warning(f"RenderCV not available: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RenderCV Backend")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="""
## RenderCV Backend API

A high-performance API for generating professional resumes using the RenderCV engine.

### Features

- **PDF Generation**: Create high-quality PDFs using multiple professional themes
- **PNG Thumbnails**: Export individual pages as PNGs for thumbnails or sharing
- **Multiple Themes**: Classic, SB2Nov, ModernCV, and Engineering Resumes
- **Format Conversion**: Export to PDF or PNG formats

### Quick Start

1. Send your resume data to `/api/render/pdf/preview` to get a PDF preview
2. Use `/api/render/pdf` to generate the final PDF
3. Generate PNG thumbnails with `/api/render/png`
4. Check available themes at `/api/templates`

### Data Format

The API accepts resume data in JSON format matching the frontend structure:
- `personalInfo`: Name, email, phone, location, links
- `summary`: Professional summary
- `experience`: Work experience entries
- `education`: Education entries
- `skills`: Skill categories
- `projects`: Project entries
        """,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Add global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An internal error occurred",
                "detail": str(exc) if settings.debug else "Please try again later"
            }
        )
    
    # Include API routes
    app.include_router(router, prefix="/api")
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs",
            "api": "/api"
        }
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
