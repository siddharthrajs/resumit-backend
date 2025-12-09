"""Resume data models matching the frontend structure."""
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class PersonalInfo(BaseModel):
    """Personal information section of the resume."""
    name: str = Field(..., max_length=100, description="Full name")
    title: Optional[str] = Field(None, max_length=100, description="Professional title/headline")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="Location (City, State/Country)")
    website: Optional[str] = Field(None, description="Personal website URL")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL or username")
    github: Optional[str] = Field(None, description="GitHub username or URL")


class Experience(BaseModel):
    """Work experience entry."""
    id: Optional[str] = Field(None, description="Unique identifier")
    company: str = Field(..., min_length=1, description="Company name")
    position: str = Field(..., min_length=1, description="Job title/position")
    location: Optional[str] = Field(None, description="Job location")
    start_date: str = Field(..., alias="startDate", description="Start date (e.g., 'Jan 2020')")
    end_date: Optional[str] = Field(None, alias="endDate", description="End date or 'Present'")
    current: bool = Field(False, description="Is this the current job?")
    description: List[str] = Field(default_factory=list, description="Bullet points/responsibilities")

    class Config:
        populate_by_name = True

    @field_validator("description", mode="before")
    @classmethod
    def filter_empty_descriptions(cls, v):
        """Filter out empty strings from description list."""
        if isinstance(v, list):
            return [item for item in v if item and item.strip()]
        return v


class Education(BaseModel):
    """Education entry."""
    id: Optional[str] = Field(None, description="Unique identifier")
    institution: str = Field(..., min_length=1, description="School/University name")
    degree: str = Field(..., description="Degree type (e.g., 'Bachelor of Science')")
    field: Optional[str] = Field(None, description="Field of study")
    location: Optional[str] = Field(None, description="Institution location")
    start_date: str = Field(..., alias="startDate", description="Start date/year")
    end_date: Optional[str] = Field(None, alias="endDate", description="End date/year")
    gpa: Optional[str] = Field(None, description="GPA (optional)")
    highlights: List[str] = Field(default_factory=list, description="Notable achievements")

    class Config:
        populate_by_name = True


class Skill(BaseModel):
    """Skills category."""
    id: Optional[str] = Field(None, description="Unique identifier")
    category: str = Field(..., min_length=1, description="Skill category name")
    items: List[str] = Field(default_factory=list, description="List of skills in this category")

    @field_validator("items", mode="before")
    @classmethod
    def filter_empty_items(cls, v):
        """Filter out empty strings from items list."""
        if isinstance(v, list):
            return [item for item in v if item and item.strip()]
        return v


class Project(BaseModel):
    """Project entry."""
    id: Optional[str] = Field(None, description="Unique identifier")
    name: str = Field(..., min_length=1, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")
    link: Optional[str] = Field(None, description="Project URL")
    start_date: Optional[str] = Field(None, alias="startDate", description="Start date")
    end_date: Optional[str] = Field(None, alias="endDate", description="End date")

    class Config:
        populate_by_name = True


class ResumeData(BaseModel):
    """Complete resume data structure matching frontend format."""
    personal_info: PersonalInfo = Field(..., alias="personalInfo")
    summary: Optional[str] = Field(None, description="Professional summary")
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    section_order: Optional[List[str]] = Field(
        None, 
        alias="sectionOrder",
        description="Order of sections to render"
    )

    class Config:
        populate_by_name = True


# Available themes
ThemeType = Literal["classic", "sb2nov", "moderncv", "engineeringresumes"]


class RenderRequest(BaseModel):
    """Request model for rendering a resume."""
    resume_data: ResumeData = Field(..., alias="resumeData")
    theme: ThemeType = Field("classic", description="Theme to use for rendering")
    output_format: Literal["pdf", "svg", "png", "all"] = Field(
        "pdf", 
        alias="outputFormat",
        description="Output format"
    )
    page_size: Literal["a4", "letter"] = Field("a4", alias="pageSize")
    
    class Config:
        populate_by_name = True


class RenderResponse(BaseModel):
    """Response model for render requests."""
    success: bool
    message: str
    pdf_url: Optional[str] = Field(None, alias="pdfUrl")
    svg_data: Optional[str] = Field(None, alias="svgData")
    png_url: Optional[str] = Field(None, alias="pngUrl")
    render_time_ms: Optional[float] = Field(None, alias="renderTimeMs")
    
    class Config:
        populate_by_name = True


class TemplateInfo(BaseModel):
    """Information about a resume template/theme."""
    id: str
    name: str
    description: str
    preview_url: Optional[str] = Field(None, alias="previewUrl")
    features: List[str] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "unhealthy"]
    version: str
    timestamp: datetime
    rendercv_available: bool = Field(alias="rendercvAvailable")
    
    class Config:
        populate_by_name = True

