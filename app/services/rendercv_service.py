"""
RenderCV Service - Core rendering logic using the RenderCV engine.

This service handles:
- Converting frontend ResumeData to RenderCV format
- Generating PDF files using RenderCV
- Converting PDF pages to SVG for real-time preview
- Managing temporary files and cleanup
"""
import asyncio
import base64
import hashlib
import io
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import logging

import yaml

from app.models.resume import ResumeData, RenderRequest
from app.services.converter import ResumeConverter
from app.services.cache import (
    cache_get_bytes,
    cache_get_json,
    cache_set_bytes,
    cache_set_json,
)
from app.config import get_settings

logger = logging.getLogger(__name__)


class RenderCVService:
    """Service for rendering resumes using RenderCV engine."""
    
    # Available themes with their descriptions
    THEMES = {
        "classic": {
            "name": "Classic",
            "description": "A clean, professional layout with a traditional feel",
            "features": ["Clean typography", "Traditional layout", "Professional appearance"]
        },
        "sb2nov": {
            "name": "SB2Nov",
            "description": "Modern, minimalist design inspired by software engineering resumes",
            "features": ["Minimalist design", "Tech-focused", "ATS-friendly"]
        },
        "moderncv": {
            "name": "ModernCV",
            "description": "Contemporary design with sidebar and modern typography",
            "features": ["Modern layout", "Sidebar design", "Color accents"]
        },
        "engineeringresumes": {
            "name": "Engineering Resumes",
            "description": "Optimized for technical roles with emphasis on projects and skills",
            "features": ["Technical focus", "Project highlights", "Skills-first layout"]
        }
    }
    
    def __init__(self):
        self.settings = get_settings()
        self._ensure_output_dir()
        self.render_cache_ttl = max(60, self.settings.cache_ttl)  # ensure reasonable TTL
    
    def _ensure_output_dir(self):
        """Ensure the output directory exists."""
        os.makedirs(self.settings.output_dir, exist_ok=True)
    
    def _generate_cache_key(self, resume_data: ResumeData, theme: str, page_size: str = "a4") -> str:
        """Generate a cache key for the render request."""
        # Create a hash of the resume data and theme
        data_str = f"{resume_data.model_dump_json()}{theme}{page_size}"
        return hashlib.md5(data_str.encode()).hexdigest()[:16]
    
    async def render_pdf(
        self, 
        resume_data: ResumeData, 
        theme: str = "classic",
        page_size: str = "a4"
    ) -> Tuple[bytes, float]:
        """
        Render resume data to PDF using RenderCV.

        Args:
            resume_data: The resume data to render
            theme: The theme to use (classic, sb2nov, moderncv, engineeringresumes, engineeringclassic)

        Returns:
            Tuple of (PDF bytes, render time in milliseconds)
        """
        start_time = time.time()

        cache_key = f"render:pdf:{self._generate_cache_key(resume_data, theme, page_size)}"
        cached_pdf = await cache_get_bytes(cache_key)
        if cached_pdf:
            return cached_pdf, 0.0  # cached hit, no render time
        
        # Convert to RenderCV dictionary format
        rendercv_dict = ResumeConverter.to_rendercv_dict(resume_data, theme, page_size)
        
        logger.debug(f"Generated RenderCV dict: {rendercv_dict}")
        
        # Create a temporary directory for the render
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.pdf"
            
            try:
                # Import and use RenderCV's new API
                import rendercv
                
                # Use the new API function
                result = rendercv.create_a_pdf_from_a_python_dictionary(
                    rendercv_dict,
                    output_path
                )
                
                # Check for validation errors
                if result is not None and len(result) > 0:
                    # result contains validation errors
                    error_messages = []
                    for error in result:
                        loc = '.'.join(str(x) for x in error.get('loc', []))
                        msg = error.get('msg', 'Unknown error')
                        error_messages.append(f"{loc}: {msg}")
                    
                    logger.warning(f"RenderCV validation errors: {error_messages}")
                    
                    # Try rendering without problematic fields
                    if any('phone' in str(e.get('loc', [])) for e in result):
                        # Remove phone and retry
                        logger.info("Retrying without phone number")
                        if 'phone' in rendercv_dict.get('cv', {}):
                            del rendercv_dict['cv']['phone']
                        result = rendercv.create_a_pdf_from_a_python_dictionary(
                            rendercv_dict,
                            output_path
                        )
                
                # Check if PDF was created
                if not output_path.exists():
                    if result:
                        error_details = "; ".join(
                            f"{'.'.join(str(x) for x in e.get('loc', []))}: {e.get('msg', '')}"
                            for e in result
                        )
                        raise ValueError(f"Validation failed: {error_details}")
                    raise FileNotFoundError("RenderCV did not generate a PDF file")
                
                # Read the PDF content
                with open(output_path, "rb") as f:
                    pdf_bytes = f.read()
                
                render_time = (time.time() - start_time) * 1000
                
                logger.info(f"PDF rendered successfully in {render_time:.2f}ms")

                # Cache the PDF for reuse
                await cache_set_bytes(cache_key, pdf_bytes, ttl=self.render_cache_ttl)
                
                return pdf_bytes, render_time
                
            except ImportError as e:
                logger.error(f"Failed to import RenderCV: {e}")
                raise RuntimeError(f"RenderCV not available: {e}")
            except Exception as e:
                logger.error(f"RenderCV render failed: {e}")
                raise RuntimeError(f"Failed to render PDF: {e}")
    
    async def render_svg(
        self, 
        resume_data: ResumeData, 
        theme: str = "classic",
        page: int = 1,
        page_size: str = "a4"
    ) -> Tuple[str, float]:
        """
        Render resume data to SVG for preview.
        
        This first generates a PDF using RenderCV, then converts the specified
        page to SVG for frontend display.
        
        Args:
            resume_data: The resume data to render
            theme: The theme to use
            page: Page number to render (1-indexed)
        
        Returns:
            Tuple of (SVG string, render time in milliseconds)
        """
        start_time = time.time()

        cache_key_svg = f"render:svg:{self._generate_cache_key(resume_data, theme, page_size)}:p{page}"
        cached_svg = await cache_get_json(cache_key_svg)
        if cached_svg and "svg" in cached_svg:
            return cached_svg["svg"], cached_svg.get("render_time", 0.0)
        
        try:
            # First, generate the PDF
            pdf_bytes, _ = await self.render_pdf(resume_data, theme, page_size)
            
            # Convert PDF to SVG using pdf2image and cairosvg
            svg_str = await self._pdf_to_svg(pdf_bytes, page)
            
            render_time = (time.time() - start_time) * 1000
            
            logger.info(f"SVG rendered successfully in {render_time:.2f}ms")

            await cache_set_json(
                cache_key_svg,
                {"svg": svg_str, "render_time": render_time},
                ttl=self.render_cache_ttl,
            )
            
            return svg_str, render_time
            
        except Exception as e:
            logger.error(f"SVG render failed: {e}")
            # Return an error SVG
            error_svg = self._generate_error_svg(str(e))
            render_time = (time.time() - start_time) * 1000
            return error_svg, render_time
    
    async def _pdf_to_svg(self, pdf_bytes: bytes, page: int = 1) -> str:
        """
        Convert PDF bytes to SVG string.
        
        Tries PyMuPDF first (doesn't require poppler), then falls back to pdf2image.
        """
        # Try PyMuPDF first (no external dependencies)
        try:
            import fitz  # PyMuPDF
            
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            if page > len(doc):
                page = 1
            
            # Get the page (0-indexed)
            pdf_page = doc[page - 1]
            
            # Render to pixmap at higher resolution for quality
            mat = fitz.Matrix(2.0, 2.0)  # 2x scale
            pix = pdf_page.get_pixmap(matrix=mat)
            
            # Convert to PNG bytes
            png_bytes = pix.tobytes("png")
            
            # Convert to base64
            img_base64 = base64.b64encode(png_bytes).decode("utf-8")
            
            doc.close()
            
            # Create SVG with embedded image (A4: 595 × 842 points)
            svg_str = f'''<svg xmlns="http://www.w3.org/2000/svg" 
                viewBox="0 0 595 842" 
                width="595" 
                height="842">
                <rect width="595" height="842" fill="#ffffff"/>
                <image 
                    href="data:image/png;base64,{img_base64}" 
                    x="0" y="0" 
                    width="595" height="842" 
                    preserveAspectRatio="xMidYMid meet"/>
            </svg>'''
            
            return svg_str
            
        except ImportError:
            logger.info("PyMuPDF not available, trying pdf2image")
        except Exception as e:
            logger.warning(f"PyMuPDF conversion failed: {e}, trying pdf2image")
        
        # Fallback to pdf2image (requires poppler)
        try:
            from pdf2image import convert_from_bytes
            
            # Convert PDF to images at high resolution
            images = convert_from_bytes(
                pdf_bytes, 
                dpi=150,
                first_page=page,
                last_page=page,
                fmt="png"
            )
            
            if not images:
                raise ValueError("No pages generated from PDF")
            
            img = images[0]
            
            # Convert PIL image to base64 PNG
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
            
            # Create SVG with embedded image
            svg_str = f'''<svg xmlns="http://www.w3.org/2000/svg" 
                viewBox="0 0 595 842" 
                width="595" 
                height="842">
                <rect width="595" height="842" fill="#ffffff"/>
                <image 
                    href="data:image/png;base64,{img_base64}" 
                    x="0" y="0" 
                    width="595" height="842" 
                    preserveAspectRatio="xMidYMid meet"/>
            </svg>'''
            
            return svg_str
            
        except ImportError as e:
            logger.warning(f"pdf2image not available: {e}")
        except Exception as e:
            logger.error(f"pdf2image conversion failed: {e}")
        
        return self._generate_error_svg("Preview generation failed - install PyMuPDF or poppler")
    
    async def _pdf_to_svg_fallback(self, pdf_bytes: bytes, page: int = 1) -> str:
        """
        Fallback method to convert PDF to SVG when pdf2image is not available.
        Uses PyMuPDF (fitz) if available.
        """
        try:
            import fitz  # PyMuPDF
            
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            if page > len(doc):
                page = 1
            
            # Get the page (0-indexed)
            pdf_page = doc[page - 1]
            
            # Render to pixmap at higher resolution
            mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better quality
            pix = pdf_page.get_pixmap(matrix=mat)
            
            # Convert to PNG bytes
            png_bytes = pix.tobytes("png")
            
            # Convert to base64
            img_base64 = base64.b64encode(png_bytes).decode("utf-8")
            
            doc.close()
            
            # Create SVG with embedded image
            svg_str = f'''<svg xmlns="http://www.w3.org/2000/svg" 
                viewBox="0 0 595 842" 
                width="595" 
                height="842">
                <rect width="595" height="842" fill="#ffffff"/>
                <image 
                    href="data:image/png;base64,{img_base64}" 
                    x="0" y="0" 
                    width="595" height="842" 
                    preserveAspectRatio="xMidYMid meet"/>
            </svg>'''
            
            return svg_str
            
        except ImportError:
            logger.warning("PyMuPDF not available, generating placeholder SVG")
            return self._generate_placeholder_svg()
        except Exception as e:
            logger.error(f"Fallback PDF to SVG failed: {e}")
            return self._generate_error_svg(str(e))
    
    def _generate_placeholder_svg(self) -> str:
        """Generate a placeholder SVG when rendering is not available."""
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 595 842" width="595" height="842">
            <rect width="595" height="842" fill="#ffffff"/>
            <rect x="40" y="40" width="515" height="60" fill="#f3f4f6" rx="4"/>
            <rect x="40" y="120" width="300" height="20" fill="#e5e7eb" rx="2"/>
            <rect x="40" y="160" width="515" height="1" fill="#d1d5db"/>
            <rect x="40" y="180" width="150" height="16" fill="#e5e7eb" rx="2"/>
            <rect x="40" y="210" width="515" height="80" fill="#f9fafb" rx="4"/>
            <rect x="40" y="310" width="150" height="16" fill="#e5e7eb" rx="2"/>
            <rect x="40" y="340" width="515" height="120" fill="#f9fafb" rx="4"/>
            <text x="297.5" y="750" text-anchor="middle" font-family="system-ui" font-size="14" fill="#9ca3af">
                Preview will appear here
            </text>
        </svg>'''
    
    def _generate_error_svg(self, error_message: str) -> str:
        """Generate an error SVG with the given message."""
        # Escape XML special characters
        safe_message = (
            error_message
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )[:100]  # Truncate for display
        
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 595 842" width="595" height="842">
            <rect width="595" height="842" fill="#ffffff"/>
            <rect x="40" y="350" width="515" height="140" fill="#fef2f2" stroke="#fecaca" rx="8"/>
            <circle cx="297.5" cy="400" r="20" fill="#fee2e2"/>
            <text x="297.5" y="408" text-anchor="middle" font-size="24" fill="#dc2626">!</text>
            <text x="297.5" y="450" text-anchor="middle" font-family="system-ui" font-size="14" fill="#dc2626" font-weight="500">
                Render Error
            </text>
            <text x="297.5" y="475" text-anchor="middle" font-family="system-ui" font-size="11" fill="#991b1b">
                {safe_message}
            </text>
        </svg>'''
    
    async def render_png(
        self, 
        resume_data: ResumeData, 
        theme: str = "classic",
        page: int = 1,
        dpi: int = 150,
        page_size: str = "a4"
    ) -> Tuple[bytes, float]:
        """
        Render resume data to PNG image.
        
        Args:
            resume_data: The resume data to render
            theme: The theme to use
            page: Page number to render (1-indexed)
            dpi: Resolution in dots per inch
        
        Returns:
            Tuple of (PNG bytes, render time in milliseconds)
        """
        start_time = time.time()
        
        try:
            # First, generate the PDF
            pdf_bytes, _ = await self.render_pdf(resume_data, theme, page_size)
            
            # Convert PDF to PNG
            from pdf2image import convert_from_bytes
            
            images = convert_from_bytes(
                pdf_bytes,
                dpi=dpi,
                first_page=page,
                last_page=page,
                fmt="png"
            )
            
            if not images:
                raise ValueError("No pages generated from PDF")
            
            # Convert to bytes
            buffer = io.BytesIO()
            images[0].save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            png_bytes = buffer.read()
            
            render_time = (time.time() - start_time) * 1000
            
            return png_bytes, render_time
            
        except Exception as e:
            logger.error(f"PNG render failed: {e}")
            raise RuntimeError(f"Failed to render PNG: {e}")
    
    def get_available_themes(self) -> List[Dict[str, Any]]:
        """Get list of available themes with their information."""
        themes = []
        for theme_id, info in self.THEMES.items():
            themes.append({
                "id": theme_id,
                "name": info["name"],
                "description": info["description"],
                "features": info["features"],
                "previewUrl": f"/api/themes/{theme_id}/preview"
            })
        return themes
    
    async def check_rendercv_available(self) -> bool:
        """Check if RenderCV is available and working."""
        try:
            import rendercv
            # Check that the main function exists
            return hasattr(rendercv, 'create_a_pdf_from_a_python_dictionary')
        except ImportError:
            return False
    
    async def get_theme_preview(self, theme: str) -> Optional[bytes]:
        """
        Get a preview image for a theme.
        Generates a sample resume with the given theme.
        """
        # Create sample resume data
        sample_data = ResumeData(
            personalInfo={
                "name": "John Doe",
                "title": "Software Engineer",
                "email": "john@example.com",
                "phone": "+1 (555) 123-4567",
                "location": "San Francisco, CA",
                "website": "johndoe.com",
                "linkedin": "linkedin.com/in/johndoe",
                "github": "github.com/johndoe"
            },
            summary="Experienced software engineer with 5+ years of expertise in building scalable web applications.",
            experience=[
                {
                    "id": "1",
                    "company": "Tech Corp",
                    "position": "Senior Software Engineer",
                    "location": "San Francisco, CA",
                    "startDate": "Jan 2021",
                    "endDate": "Present",
                    "current": True,
                    "description": [
                        "Led development of microservices architecture",
                        "Mentored junior developers"
                    ]
                }
            ],
            education=[
                {
                    "id": "1",
                    "institution": "University of California",
                    "degree": "Bachelor of Science",
                    "field": "Computer Science",
                    "location": "Berkeley, CA",
                    "startDate": "2014",
                    "endDate": "2018",
                    "gpa": "3.8",
                    "highlights": []
                }
            ],
            skills=[
                {"id": "1", "category": "Languages", "items": ["Python", "TypeScript", "Go"]},
                {"id": "2", "category": "Frameworks", "items": ["FastAPI", "React", "Django"]}
            ],
            projects=[]
        )
        
        try:
            png_bytes, _ = await self.render_png(sample_data, theme, dpi=100)
            return png_bytes
        except Exception as e:
            logger.error(f"Failed to generate theme preview: {e}")
            return None
