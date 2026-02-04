"""Resume parsing service using Google Gemini (google-genai SDK)."""
import logging
import uuid
from typing import Optional, List

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.config import get_settings
from app.models.resume import ResumeData

logger = logging.getLogger(__name__)

# Pydantic models for structured output
class ParsedPersonalInfo(BaseModel):
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None


class ParsedExperience(BaseModel):
    company: str
    position: str
    location: Optional[str] = None
    startDate: str = Field(description="Start date in YYYY-MM or YYYY format (e.g., '2020-01' or '2020')")
    endDate: Optional[str] = Field(default=None, description="End date in YYYY-MM or YYYY format, or 'present' for current positions")
    current: bool = Field(default=False, description="True if this is the current job (endDate is 'present')")
    description: List[str] = Field(default=[], description="List of bullet points describing responsibilities and achievements")


class ParsedEducation(BaseModel):
    institution: str = Field(description="Name of school, college, or university")
    degree: str = Field(description="Degree type (e.g., 'BS', 'Bachelor of Science', 'MS', 'PhD')")
    field: Optional[str] = Field(default=None, description="Field of study or major")
    location: Optional[str] = None
    startDate: str = Field(description="Start date in YYYY-MM or YYYY format (e.g., '2018-09' or '2018')")
    endDate: Optional[str] = Field(default=None, description="End date in YYYY-MM or YYYY format, or 'present' for ongoing education")
    gpa: Optional[str] = None
    highlights: List[str] = Field(default=[], description="List of achievements, honors, or relevant coursework")


class ParsedSkill(BaseModel):
    category: str
    items: List[str] = []


class ParsedProject(BaseModel):
    name: str = Field(description="Project name")
    description: Optional[str] = Field(default=None, description="Brief project description")
    highlights: List[str] = Field(default=[], description="Key achievements or features")
    technologies: List[str] = Field(default=[], description="Technologies, frameworks, and tools used")
    link: Optional[str] = Field(default=None, description="Project URL or repository link")
    startDate: Optional[str] = Field(default=None, description="Start date in YYYY-MM or YYYY format")
    endDate: Optional[str] = Field(default=None, description="End date in YYYY-MM or YYYY format, or 'present'")


class ParsedResume(BaseModel):
    personalInfo: ParsedPersonalInfo
    summary: Optional[str] = None
    experience: List[ParsedExperience] = []
    education: List[ParsedEducation] = []
    skills: List[ParsedSkill] = []
    projects: List[ParsedProject] = []


PARSE_PROMPT = """You are a professional resume parser. Extract structured information from the resume text and return it as JSON. For all null values just leave them blank. Donot use null for any field.

## CRITICAL DATE FORMAT RULES (MUST FOLLOW EXACTLY):
All dates MUST be in one of these formats ONLY:
- "YYYY-MM-DD" (e.g., "2020-01-15")
- "YYYY-MM" (e.g., "2020-01") - USE THIS for most cases
- "YYYY" (e.g., "2020")
- "present" (lowercase, for current/ongoing positions)

NEVER use formats like "Jan 2020", "January 2020", "01/2020", or "2020-present".
Convert "Present", "Current", "Now", "Ongoing" to lowercase "present".

Examples of date conversion:
- "Jan 2020" → "2020-01"
- "January 2020" → "2020-01"
- "2020" → "2020"
- "Sept 2018" → "2018-09"
- "Present" → "present"
- "Current" → "present"
- "June 2023" → "2023-06"

## EXTRACTION RULES:
1. personalInfo.name is REQUIRED - extract the person's full name
2. Use null for missing optional fields - NEVER make up data
3. Keep bullet points concise, preserve original wording
4. Group skills into logical categories (e.g., "Programming Languages", "Frameworks", "Tools", "Soft Skills")
5. If a section doesn't exist in the resume, use an empty array []
6. Preserve technical terms, company names, and proper nouns exactly as written
7. Set current=true for jobs/education that are ongoing (endDate="present")
8. For education, extract degree type (e.g., "BS", "MS", "PhD", "Bachelor of Science")
9. For LinkedIn/GitHub, extract just the username if possible, or the full URL

## Month number reference:
Jan=01, Feb=02, Mar=03, Apr=04, May=05, Jun=06, Jul=07, Aug=08, Sep=09, Oct=10, Nov=11, Dec=12

Resume text to parse:
---
{resume_text}
---"""


def _generate_id() -> str:
    """Generate a unique ID for resume entries."""
    return str(uuid.uuid4())[:8]


def _add_ids_to_data(data: dict) -> dict:
    """Add unique IDs to all list entries."""
    if "experience" in data:
        for entry in data["experience"]:
            entry["id"] = _generate_id()

    if "education" in data:
        for entry in data["education"]:
            entry["id"] = _generate_id()

    if "skills" in data:
        for entry in data["skills"]:
            entry["id"] = _generate_id()

    if "projects" in data:
        for entry in data["projects"]:
            entry["id"] = _generate_id()

    return data

def parse_resume_with_llm(resume_text: str) -> Optional[ResumeData]:
    """
    Parse resume text using Google Gemini and return structured data.

    Args:
        resume_text: The extracted text from the resume PDF

    Returns:
        ResumeData object if successful, None if parsing fails
    """
    settings = get_settings()

    if not settings.gemini_api_key:
        logger.error("RENDERCV_GEMINI_API_KEY not configured")
        raise ValueError("Gemini API key not configured")

    # Create client with API key
    client = genai.Client(api_key=settings.gemini_api_key)

    # Build the prompt
    prompt = PARSE_PROMPT.replace("{resume_text}", resume_text)

    try:
        logger.info("Sending resume to Gemini for parsing...")

        # Generate content with structured output
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.95,
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_schema=ParsedResume,
            ),
        )

        # Get the parsed response
        parsed_resume: ParsedResume = response.parsed

        if parsed_resume is None:
            raise ValueError("Failed to parse response from Gemini")

        logger.info("Successfully parsed resume with Gemini")

        # Convert to dict and add IDs
        parsed_data = parsed_resume.model_dump()
        parsed_data = _add_ids_to_data(parsed_data)

        # Validate with our ResumeData model
        resume_data = ResumeData.model_validate(parsed_data)

        return resume_data

    except Exception as e:
        logger.error(f"Gemini parsing failed: {e}")
        raise
