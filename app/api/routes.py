"""
API Routes for RenderCV Backend.

Provides endpoints for:
- Rendering resumes to PDF
- Generating SVG previews for real-time updates
- Listing available themes
- Health checks
"""
import base64
from datetime import datetime
from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, Query, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
import io

from app.models.resume import (
    ResumeData,
    RenderRequest,
    RenderResponse,
    TemplateInfo,
    HealthResponse,
    ATSScoreRequest,
    ATSScoreResponse,
    SectionScoreResponse,
    KeywordAnalysisResponse,
    FormatAnalysisResponse,
    ContentQualityResponse,
)
from app.services.rendercv_service import RenderCVService
from app.services.ats_scorer import get_ats_scorer
from app.services.cache import cache_get_json, cache_set_json
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize service
rendercv_service = RenderCVService()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the service status, version, and whether RenderCV is available.
    """
    settings = get_settings()
    rendercv_available = await rendercv_service.check_rendercv_available()
    
    return HealthResponse(
        status="healthy" if rendercv_available else "unhealthy",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        rendercvAvailable=rendercv_available
    )


@router.post("/render/svg", tags=["Render"])
async def render_svg(request: RenderRequest):
    """
    Render resume to SVG for real-time preview.
    
    This endpoint is optimized for speed to enable live preview updates.
    Returns an SVG string that can be directly embedded in the frontend.
    
    Request body:
    - resumeData: The resume data matching the frontend format
    - theme: Theme to use (classic, sb2nov, moderncv, engineeringresumes, engineeringclassic)

    Returns:
    - success: Whether rendering succeeded
    - svgData: The SVG string
    - renderTimeMs: Time taken to render in milliseconds
    """
    try:
        svg_data, render_time = await rendercv_service.render_svg(
            request.resume_data,
            request.theme,
            page_size=request.page_size
        )
        
        return RenderResponse(
            success=True,
            message="SVG rendered successfully",
            svgData=svg_data,
            renderTimeMs=render_time
        )
    except Exception as e:
        logger.error(f"SVG render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/render/pdf", tags=["Render"])
async def render_pdf(
    request: RenderRequest,
    download: bool = Query(False, description="If true, returns file download instead of JSON")
):
    """
    Render resume to PDF.
    
    This endpoint generates a high-quality PDF using RenderCV.
    
    Request body:
    - resumeData: The resume data matching the frontend format
    - theme: Theme to use (classic, sb2nov, moderncv, engineeringresumes, engineeringclassic)

    Query parameters:
    - download: If true, returns the PDF as a file download
    
    Returns:
    - If download=false: JSON response with base64-encoded PDF
    - If download=true: PDF file download
    """
    try:
        pdf_bytes, render_time = await rendercv_service.render_pdf(
            request.resume_data,
            request.theme,
            request.page_size
        )
        
        if download:
            # Return as file download
            filename = f"{request.resume_data.personal_info.name.replace(' ', '_')}_Resume.pdf"
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "X-Render-Time-Ms": str(render_time)
                }
            )
        
        # Return as JSON with base64-encoded PDF
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        
        return {
            "success": True,
            "message": "PDF rendered successfully",
            "pdfData": pdf_base64,
            "renderTimeMs": render_time,
            "mimeType": "application/pdf"
        }
        
    except Exception as e:
        logger.error(f"PDF render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/render/pdf/preview", tags=["Render"])
async def render_pdf_preview(request: RenderRequest):
    """
    Render resume to PDF and return raw bytes for preview.

    This endpoint is optimized for the PDF.js viewer on the frontend.
    Returns raw PDF bytes with appropriate headers.

    Request body:
    - resumeData: The resume data matching the frontend format
    - theme: Theme to use (classic, sb2nov, moderncv, engineeringresumes, engineeringclassic)
    - pageSize: Page size (a4 or letter)
    """
    try:
        pdf_bytes, render_time = await rendercv_service.render_pdf(
            request.resume_data,
            request.theme,
            request.page_size
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "X-Render-Time-Ms": str(render_time),
                "Cache-Control": "no-cache",
            }
        )

    except Exception as e:
        logger.error(f"PDF preview render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/render/png", tags=["Render"])
async def render_png(
    request: RenderRequest,
    page: int = Query(1, ge=1, description="Page number to render"),
    dpi: int = Query(150, ge=72, le=300, description="Resolution in DPI"),
    download: bool = Query(False, description="If true, returns file download")
):
    """
    Render resume to PNG image.
    
    Useful for generating preview thumbnails or social media images.
    
    Query parameters:
    - page: Page number to render (default: 1)
    - dpi: Resolution in dots per inch (72-300, default: 150)
    - download: If true, returns PNG as file download
    """
    try:
        png_bytes, render_time = await rendercv_service.render_png(
            request.resume_data,
            request.theme,
            page=page,
            dpi=dpi,
            page_size=request.page_size
        )
        
        if download:
            filename = f"{request.resume_data.personal_info.name.replace(' ', '_')}_Resume.png"
            return StreamingResponse(
                io.BytesIO(png_bytes),
                media_type="image/png",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "X-Render-Time-Ms": str(render_time)
                }
            )
        
        # Return as JSON with base64-encoded PNG
        png_base64 = base64.b64encode(png_bytes).decode("utf-8")
        
        return {
            "success": True,
            "message": "PNG rendered successfully",
            "pngData": png_base64,
            "renderTimeMs": render_time,
            "mimeType": "image/png"
        }
        
    except Exception as e:
        logger.error(f"PNG render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=list[TemplateInfo], tags=["Templates"])
async def list_templates():
    """
    List all available resume templates/themes.
    
    Returns information about each theme including:
    - id: Theme identifier
    - name: Display name
    - description: Brief description
    - features: Key features of the theme
    - previewUrl: URL to get a preview image
    """
    cache_key = "templates:v1"
    cached = await cache_get_json(cache_key)
    if cached:
        return [TemplateInfo(**theme) for theme in cached]

    themes = rendercv_service.get_available_themes()
    await cache_set_json(cache_key, themes, ttl=3600)
    return [TemplateInfo(**theme) for theme in themes]


@router.get("/templates/{theme_id}/preview", tags=["Templates"])
async def get_template_preview(theme_id: str):
    """
    Get a preview image of a theme.
    
    Generates a sample resume with the specified theme and returns it as a PNG image.
    """
    if theme_id not in rendercv_service.THEMES:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    
    try:
        png_bytes = await rendercv_service.get_theme_preview(theme_id)
        
        if png_bytes is None:
            raise HTTPException(status_code=500, detail="Failed to generate preview")
        
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}  # Cache for 1 hour
        )
        
    except Exception as e:
        logger.error(f"Theme preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/yaml", tags=["Utilities"])
async def convert_to_yaml(resume_data: ResumeData, theme: str = Query("classic")):
    """
    Convert frontend ResumeData to RenderCV YAML format.
    
    Useful for debugging or exporting resume data in RenderCV format.
    """
    from app.services.converter import ResumeConverter
    
    try:
        yaml_content = ResumeConverter.to_rendercv_yaml(resume_data, theme)
        
        return {
            "success": True,
            "yaml": yaml_content,
            "theme": theme
        }
        
    except Exception as e:
        logger.error(f"YAML conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", tags=["Utilities"])
async def validate_resume(resume_data: ResumeData):
    """
    Validate resume data without rendering.

    Checks if the resume data is valid and complete enough for rendering.
    Returns validation results with any warnings or suggestions.
    """
    warnings = []
    errors = []

    # Check personal info
    if not resume_data.personal_info.name:
        errors.append("Name is required")

    if not resume_data.personal_info.email:
        warnings.append("Email is recommended for contact")

    # Check content sections
    if not resume_data.experience and not resume_data.education and not resume_data.projects:
        warnings.append("Resume has no experience, education, or projects")

    # Check experience
    for i, exp in enumerate(resume_data.experience):
        if not exp.company or not exp.position:
            errors.append(f"Experience {i+1}: Company and position are required")
        if not exp.description:
            warnings.append(f"Experience {i+1}: Consider adding bullet points")

    # Check education
    for i, edu in enumerate(resume_data.education):
        if not edu.institution or not edu.degree:
            errors.append(f"Education {i+1}: Institution and degree are required")

    # Check skills
    if not resume_data.skills:
        warnings.append("Consider adding skills section")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "experienceCount": len(resume_data.experience),
            "educationCount": len(resume_data.education),
            "skillCategories": len(resume_data.skills),
            "projectCount": len(resume_data.projects),
            "hasSummary": bool(resume_data.summary)
        }
    }


@router.post("/ats/analyze", response_model=ATSScoreResponse, tags=["ATS"])
async def analyze_ats_score(request: ATSScoreRequest):
    """
    Perform comprehensive ATS (Applicant Tracking System) analysis on a resume.

    This endpoint analyzes the resume based on:
    - Section completeness and quality
    - Keyword optimization
    - Format and structure
    - Content quality (action verbs, quantification)
    - Optional: Job description matching

    Request body:
    - resumeData: The resume data to analyze
    - jobDescription: (Optional) Job description for matching analysis

    Returns:
    - overallScore: 0-100 score
    - grade: Letter grade (A+, A, B+, etc.)
    - sectionScores: Detailed breakdown by section
    - keywordAnalysis: Technical and soft skill keywords found
    - formatAnalysis: Structure and format assessment
    - contentQuality: Metrics on bullets, quantification, action verbs
    - topIssues: Priority issues to fix
    - topSuggestions: Actionable improvements
    - strengths: What the resume does well
    - jobMatchScore: (If job description provided) Match percentage
    - matchedKeywords: Keywords found in both resume and JD
    - missingKeywords: Important JD keywords not in resume
    """
    import time
    start_time = time.time()

    try:
        ats_scorer = get_ats_scorer()
        result = ats_scorer.analyze(
            request.resume_data,
            request.job_description
        )

        analysis_time = (time.time() - start_time) * 1000

        # Convert dataclasses to response models
        section_scores = [
            SectionScoreResponse(
                name=s.name,
                score=int(s.score),
                weight=s.weight,
                issues=s.issues,
                suggestions=s.suggestions,
                highlights=s.highlights
            )
            for s in result.section_scores
        ]

        keyword_analysis = KeywordAnalysisResponse(
            totalKeywords=result.keyword_analysis.total_keywords,
            technicalKeywords=result.keyword_analysis.technical_keywords,
            softSkillKeywords=result.keyword_analysis.soft_skill_keywords,
            actionVerbsUsed=result.keyword_analysis.action_verbs_used,
            missingCommonKeywords=result.keyword_analysis.missing_common_keywords,
            keywordDensity=result.keyword_analysis.keyword_density
        )

        format_analysis = FormatAnalysisResponse(
            hasClearSections=result.format_analysis.has_clear_sections,
            bulletPointConsistency=result.format_analysis.bullet_point_consistency,
            lengthAppropriate=result.format_analysis.length_appropriate,
            estimatedPages=result.format_analysis.estimated_pages,
            issues=result.format_analysis.issues
        )

        content_quality = ContentQualityResponse(
            quantifiedAchievements=result.content_quality.quantified_achievements,
            totalBulletPoints=result.content_quality.total_bullet_points,
            quantificationRate=result.content_quality.quantification_rate,
            averageBulletLength=result.content_quality.average_bullet_length,
            actionVerbUsageRate=result.content_quality.action_verb_usage_rate,
            fillerWordCount=result.content_quality.filler_word_count,
            issues=result.content_quality.issues
        )

        return ATSScoreResponse(
            success=True,
            overallScore=result.overall_score,
            grade=result.grade,
            sectionScores=section_scores,
            keywordAnalysis=keyword_analysis,
            formatAnalysis=format_analysis,
            contentQuality=content_quality,
            topIssues=result.top_issues,
            topSuggestions=result.top_suggestions,
            strengths=result.strengths,
            jobMatchScore=result.job_match_score,
            matchedKeywords=result.matched_keywords,
            missingKeywords=result.missing_keywords,
            analysisTimeMs=round(analysis_time, 2)
        )

    except Exception as e:
        logger.error(f"ATS analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

