"""Converter service to transform frontend ResumeData to RenderCV YAML format."""
import re
from typing import Dict, Any, List, Optional
import yaml
from app.models.resume import ResumeData, Experience, Education, Skill, Project


class ResumeConverter:
    """Converts frontend ResumeData format to RenderCV YAML format."""
    
    @staticmethod
    def format_date(date_str: Optional[str]) -> Optional[str]:
        """
        Format date string for RenderCV.
        RenderCV expects dates in specific formats like:
        - "2020-01" (YYYY-MM)
        - "2020" (YYYY)
        - "present" for current positions
        """
        if not date_str:
            return None
            
        date_str = date_str.strip().lower()
        
        # Handle "present" or "current"
        if date_str in ("present", "current", "now"):
            return "present"
        
        # Try to parse common formats
        # Handle "Jan 2020", "January 2020" format
        month_year_pattern = r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{4})$"
        match = re.match(month_year_pattern, date_str, re.IGNORECASE)
        if match:
            month_map = {
                "jan": "01", "feb": "02", "mar": "03", "apr": "04",
                "may": "05", "jun": "06", "jul": "07", "aug": "08",
                "sep": "09", "oct": "10", "nov": "11", "dec": "12"
            }
            month = month_map.get(match.group(1).lower()[:3], "01")
            year = match.group(2)
            return f"{year}-{month}"
        
        # Handle "2020" format (year only)
        if re.match(r"^\d{4}$", date_str):
            return date_str
        
        # Handle "2020-01" format (already correct)
        if re.match(r"^\d{4}-\d{2}$", date_str):
            return date_str
        
        # Handle "01/2020" or "1/2020" format
        slash_pattern = r"^(\d{1,2})/(\d{4})$"
        match = re.match(slash_pattern, date_str)
        if match:
            month = match.group(1).zfill(2)
            year = match.group(2)
            return f"{year}-{month}"
        
        # Return original if can't parse
        return date_str
    
    @staticmethod
    def clean_url(url: Optional[str]) -> Optional[str]:
        """Clean and format URL."""
        if not url:
            return None
        
        url = url.strip()
        
        # Remove common prefixes for cleaner display
        url = re.sub(r"^https?://(www\.)?", "", url)
        
        # Remove trailing slashes
        url = url.rstrip("/")
        
        return url
    
    @staticmethod
    def format_linkedin(linkedin: Optional[str]) -> Optional[str]:
        """Format LinkedIn URL or username."""
        if not linkedin:
            return None
        
        linkedin = linkedin.strip()
        
        # Extract username from URL
        match = re.search(r"linkedin\.com/in/([^/?]+)", linkedin)
        if match:
            return f"https://linkedin.com/in/{match.group(1)}"
        
        # If it's just a username
        if not linkedin.startswith("http"):
            # Remove any linkedin.com prefix
            linkedin = re.sub(r"^(linkedin\.com/in/)?", "", linkedin)
            return f"https://linkedin.com/in/{linkedin}"
        
        return linkedin
    
    @staticmethod
    def format_github(github: Optional[str]) -> Optional[str]:
        """Format GitHub URL or username."""
        if not github:
            return None
        
        github = github.strip()
        
        # Extract username from URL
        match = re.search(r"github\.com/([^/?]+)", github)
        if match:
            return f"https://github.com/{match.group(1)}"
        
        # If it's just a username
        if not github.startswith("http"):
            # Remove any github.com prefix
            github = re.sub(r"^(github\.com/)?", "", github)
            return f"https://github.com/{github}"
        
        return github
    
    @classmethod
    def convert_experience(cls, exp: Experience) -> Dict[str, Any]:
        """Convert a single experience entry to RenderCV format."""
        entry: Dict[str, Any] = {
            "company": exp.company,
            "position": exp.position,
        }
        
        if exp.location:
            entry["location"] = exp.location
        
        start_date = cls.format_date(exp.start_date)
        end_date = cls.format_date(exp.end_date) if exp.end_date and not exp.current else "present"
        
        if start_date:
            entry["start_date"] = start_date
        if end_date:
            entry["end_date"] = end_date
        
        if exp.description:
            entry["highlights"] = exp.description
        
        return entry
    
    @classmethod
    def convert_education(cls, edu: Education) -> Dict[str, Any]:
        """Convert a single education entry to RenderCV format."""
        # Build the study type with field
        study_type = edu.degree
        if edu.field:
            study_type = f"{edu.degree} in {edu.field}"
        
        entry: Dict[str, Any] = {
            "institution": edu.institution,
            "area": edu.field or "",
            "study_type": study_type,
        }
        
        if edu.location:
            entry["location"] = edu.location
        
        start_date = cls.format_date(edu.start_date)
        end_date = cls.format_date(edu.end_date)
        
        if start_date:
            entry["start_date"] = start_date
        if end_date:
            entry["end_date"] = end_date
        
        if edu.gpa:
            entry["gpa"] = edu.gpa
        
        if edu.highlights:
            entry["highlights"] = edu.highlights
        
        return entry
    
    @classmethod
    def convert_project(cls, proj: Project) -> Dict[str, Any]:
        """Convert a single project entry to RenderCV format."""
        entry: Dict[str, Any] = {
            "name": proj.name,
        }

        # Prioritize explicit highlights, fall back to description
        highlights: List[str] = []
        if proj.highlights:
            highlights.extend(proj.highlights)
        elif proj.description:
            highlights.append(proj.description)
        
        if proj.link:
            entry["url"] = proj.link
        
        if proj.start_date:
            entry["start_date"] = cls.format_date(proj.start_date)
        if proj.end_date:
            entry["end_date"] = cls.format_date(proj.end_date)
        
        # Add technologies as part of summary or highlights
        if proj.technologies:
            tech_str = ", ".join(proj.technologies)
            highlights.insert(0, f"Technologies: {tech_str}")

        if highlights:
            entry["highlights"] = highlights
        
        return entry
    
    @classmethod
    def convert_skills(cls, skills: List[Skill]) -> List[Dict[str, Any]]:
        """Convert skills to RenderCV format."""
        result = []
        for skill in skills:
            if skill.category and skill.items:
                result.append({
                    "label": skill.category,
                    "details": ", ".join(skill.items)
                })
        return result
    
    @classmethod
    def to_rendercv_yaml(cls, resume_data: ResumeData, theme: str = "classic", page_size: str = "a4") -> str:
        """
        Convert ResumeData to RenderCV YAML format.
        
        RenderCV YAML structure:
        ```yaml
        cv:
          name: John Doe
          label: Software Engineer
          location: San Francisco, CA
          email: john@example.com
          phone: +1 (555) 123-4567
          website: https://johndoe.com
          social_networks:
            - network: LinkedIn
              username: johndoe
            - network: GitHub
              username: johndoe
          summary: Professional summary here...
          sections:
            experience:
              - company: Tech Corp
                position: Senior Engineer
                start_date: 2020-01
                end_date: present
                highlights:
                  - Did amazing things
            education:
              - institution: University
                area: Computer Science
                study_type: BS
                start_date: 2016
                end_date: 2020
            skills:
              - label: Languages
                details: Python, JavaScript, Go
        design:
          theme: classic
        ```
        """
        pi = resume_data.personal_info
        
        # Build CV section
        cv: Dict[str, Any] = {
            "name": pi.name,
        }
        
        if pi.title:
            cv["label"] = pi.title
        
        if pi.location:
            cv["location"] = pi.location
        
        if pi.email:
            cv["email"] = pi.email
        
        if pi.phone:
            cv["phone"] = pi.phone
        
        if pi.website:
            website = pi.website
            if not website.startswith("http"):
                website = f"https://{website}"
            cv["website"] = website
        
        # Social networks
        social_networks = []
        if pi.linkedin:
            linkedin_username = re.search(r"linkedin\.com/in/([^/?]+)", pi.linkedin)
            if linkedin_username:
                social_networks.append({
                    "network": "LinkedIn",
                    "username": linkedin_username.group(1)
                })
            elif not pi.linkedin.startswith("http"):
                social_networks.append({
                    "network": "LinkedIn",
                    "username": pi.linkedin.replace("linkedin.com/in/", "")
                })
        
        if pi.github:
            github_username = re.search(r"github\.com/([^/?]+)", pi.github)
            if github_username:
                social_networks.append({
                    "network": "GitHub",
                    "username": github_username.group(1)
                })
            elif not pi.github.startswith("http"):
                social_networks.append({
                    "network": "GitHub",
                    "username": pi.github.replace("github.com/", "")
                })
        
        if social_networks:
            cv["social_networks"] = social_networks
        
        
        # Build sections
        sections: Dict[str, Any] = {}
        raw_sections = resume_data.rendercv_sections or {}

        # Determine section order, prioritizing provided order, otherwise
        # preserving the order from raw RenderCV sections, falling back to defaults.
        section_order = (
            resume_data.section_order
            or list(raw_sections.keys())
            or ["summary", "experience", "education", "skills", "projects"]
        )

        def add_section(key: str, value: Any):
            """Insert section while preserving order and skipping empty values."""
            if value is None:
                return
            sections[key] = value

        for section_key in section_order:
            if raw_sections and section_key in raw_sections:
                add_section(section_key, raw_sections[section_key])
            elif section_key == "summary" and resume_data.summary:
                # Summary is a list of strings in RenderCV
                add_section("summary", [resume_data.summary])
            elif section_key == "experience" and resume_data.experience:
                add_section(
                    "experience",
                    [cls.convert_experience(exp) for exp in resume_data.experience],
                )
            elif section_key == "education" and resume_data.education:
                add_section(
                    "education",
                    [cls.convert_education(edu) for edu in resume_data.education],
                )
            elif section_key == "skills" and resume_data.skills:
                add_section("skills", cls.convert_skills(resume_data.skills))
            elif section_key == "projects" and resume_data.projects:
                add_section(
                    "projects",
                    [cls.convert_project(proj) for proj in resume_data.projects],
                )

        # Append any remaining raw sections not explicitly ordered
        for raw_key, raw_value in raw_sections.items():
            if raw_key not in sections:
                add_section(raw_key, raw_value)
        
        if sections:
            cv["sections"] = sections
        
        # Map page sizes to RenderCV format
        rendercv_page_size = page_size
        if page_size == "letter":
            rendercv_page_size = "us-letter"

        # Build design section
        design: Dict[str, Any] = {
            "theme": theme,
            "page": {
                "size": rendercv_page_size,
            },
        }
        
        # Full YAML structure
        yaml_data = {
            "cv": cv,
            "design": design,
        }
        
        return yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    @classmethod
    def to_rendercv_dict(cls, resume_data: ResumeData, theme: str = "classic", page_size: str = "a4") -> Dict[str, Any]:
        """
        Convert ResumeData to RenderCV dictionary format.
        This is used for programmatic access to RenderCV.
        """
        yaml_str = cls.to_rendercv_yaml(resume_data, theme, page_size)
        return yaml.safe_load(yaml_str)
