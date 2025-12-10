"""
Professional-grade ATS (Applicant Tracking System) Score Analysis Service.

This module provides comprehensive resume analysis based on real ATS systems:
- Keyword extraction and matching
- Format and structure analysis
- Content quality assessment
- Section completeness scoring
- Readability metrics
- Action verb analysis
- Quantification detection
- Contact information validation

The scoring algorithm is based on industry research on how ATS systems parse
and rank resumes, including insights from Taleo, Greenhouse, Lever, and others.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.models.resume import ResumeData
from app.services.nlp_utils import NLPProcessor

logger = logging.getLogger(__name__)


# Common ATS-friendly action verbs categorized by impact
ACTION_VERBS = {
    "leadership": [
        "led", "managed", "directed", "supervised", "coordinated", "oversaw",
        "headed", "guided", "mentored", "trained", "coached", "delegated",
        "spearheaded", "championed", "pioneered", "orchestrated"
    ],
    "achievement": [
        "achieved", "accomplished", "attained", "exceeded", "surpassed", "delivered",
        "earned", "completed", "succeeded", "won", "secured", "captured"
    ],
    "creation": [
        "created", "developed", "designed", "built", "established", "founded",
        "initiated", "launched", "introduced", "originated", "produced", "generated"
    ],
    "improvement": [
        "improved", "enhanced", "increased", "boosted", "accelerated", "optimized",
        "streamlined", "upgraded", "maximized", "strengthened", "advanced", "elevated"
    ],
    "analysis": [
        "analyzed", "evaluated", "assessed", "researched", "investigated", "examined",
        "identified", "discovered", "diagnosed", "audited", "reviewed", "surveyed"
    ],
    "communication": [
        "presented", "communicated", "negotiated", "persuaded", "influenced", "collaborated",
        "partnered", "liaised", "facilitated", "mediated", "advocated", "promoted"
    ],
    "technical": [
        "implemented", "engineered", "programmed", "automated", "integrated", "configured",
        "deployed", "architected", "debugged", "refactored", "migrated", "maintained"
    ]
}

# Flatten action verbs for quick lookup
ALL_ACTION_VERBS = set()
for verbs in ACTION_VERBS.values():
    ALL_ACTION_VERBS.update(verbs)

# Common filler words to avoid
FILLER_WORDS = {
    "responsible for", "duties included", "worked on", "helped with",
    "assisted with", "participated in", "involved in", "tasked with"
}

# Industry-standard section weights for ATS scoring
SECTION_WEIGHTS = {
    "personal_info": 0.10,
    "summary": 0.10,
    "experience": 0.35,
    "education": 0.15,
    "skills": 0.20,
    "projects": 0.10,
}


@dataclass
class SectionAnalysis:
    """Analysis result for a specific resume section."""
    name: str
    score: float  # 0-100
    weight: float
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)


@dataclass
class KeywordAnalysis:
    """Analysis of keywords and their relevance."""
    total_keywords: int
    technical_keywords: list[str]
    soft_skill_keywords: list[str]
    action_verbs_used: list[str]
    missing_common_keywords: list[str]
    keyword_density: float


@dataclass
class FormatAnalysis:
    """Analysis of resume format and structure."""
    has_clear_sections: bool
    bullet_point_consistency: float  # 0-100
    length_appropriate: bool
    estimated_pages: float
    issues: list[str] = field(default_factory=list)


@dataclass
class ContentQuality:
    """Analysis of content quality metrics."""
    quantified_achievements: int
    total_bullet_points: int
    quantification_rate: float  # percentage
    average_bullet_length: float
    action_verb_usage_rate: float
    filler_word_count: int
    issues: list[str] = field(default_factory=list)


@dataclass
class ATSScoreResult:
    """Complete ATS analysis result."""
    overall_score: int  # 0-100
    grade: str  # A+, A, B+, B, C+, C, D, F
    section_scores: list[SectionAnalysis]
    keyword_analysis: KeywordAnalysis
    format_analysis: FormatAnalysis
    content_quality: ContentQuality
    top_issues: list[str]
    top_suggestions: list[str]
    strengths: list[str]
    job_match_score: Optional[int] = None  # When job description provided
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)


class ATSScorer:
    """
    Professional ATS scoring engine.

    Analyzes resumes based on:
    1. Section completeness and quality
    2. Keyword optimization
    3. Format and structure
    4. Content quality and impact
    5. Optional: Job description matching
    """

    def __init__(self):
        self.quantification_pattern = re.compile(
            r'\b(\d+[%+]?|\$[\d,.]+[KMB]?|[\d,.]+[KMB]?\+?)\b',
            re.IGNORECASE
        )
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.phone_pattern = re.compile(r'[\d\-\(\)\+\s]{10,}')
        self.url_pattern = re.compile(r'https?://[^\s]+|www\.[^\s]+')
        self.nlp = NLPProcessor()

    def analyze(
        self,
        resume_data: ResumeData,
        job_description: Optional[str] = None
    ) -> ATSScoreResult:
        """
        Perform comprehensive ATS analysis on resume data.

        Args:
            resume_data: The resume data to analyze
            job_description: Optional job description for matching analysis

        Returns:
            ATSScoreResult with detailed scoring and suggestions
        """
        # Analyze each section
        section_scores = [
            self._analyze_personal_info(resume_data),
            self._analyze_summary(resume_data),
            self._analyze_experience(resume_data),
            self._analyze_education(resume_data),
            self._analyze_skills(resume_data),
            self._analyze_projects(resume_data),
        ]

        # Calculate overall score (weighted average)
        weighted_sum = sum(s.score * s.weight for s in section_scores)
        total_weight = sum(s.weight for s in section_scores)
        base_score = weighted_sum / total_weight if total_weight > 0 else 0

        # Perform additional analyses
        keyword_analysis = self._analyze_keywords(resume_data)
        format_analysis = self._analyze_format(resume_data)
        content_quality = self._analyze_content_quality(resume_data)

        # Apply bonuses/penalties based on additional analyses
        score_adjustments = 0

        # Bonus for high quantification rate
        if content_quality.quantification_rate > 0.5:
            score_adjustments += 5
        elif content_quality.quantification_rate > 0.3:
            score_adjustments += 3

        # Bonus for strong action verb usage
        if content_quality.action_verb_usage_rate > 0.7:
            score_adjustments += 3
        elif content_quality.action_verb_usage_rate > 0.5:
            score_adjustments += 2

        # Penalty for filler words
        if content_quality.filler_word_count > 3:
            score_adjustments -= 5
        elif content_quality.filler_word_count > 1:
            score_adjustments -= 2

        # Penalty for format issues
        score_adjustments -= len(format_analysis.issues) * 2

        # Calculate final score
        overall_score = max(0, min(100, int(base_score + score_adjustments)))

        # Job matching if description provided
        job_match_score = None
        matched_keywords = []
        missing_keywords = []

        if job_description:
            job_match_score, matched_keywords, missing_keywords = self._analyze_job_match(
                resume_data, job_description
            )
            # Blend job match into overall score (30% weight when available)
            overall_score = int(overall_score * 0.7 + job_match_score * 0.3)

        # Determine grade
        grade = self._score_to_grade(overall_score)

        # Collect all issues and suggestions
        all_issues = []
        all_suggestions = []
        all_strengths = []

        for section in section_scores:
            all_issues.extend(section.issues)
            all_suggestions.extend(section.suggestions)
            all_strengths.extend(section.highlights)

        all_issues.extend(format_analysis.issues)
        all_issues.extend(content_quality.issues)

        # Sort by importance and limit
        top_issues = all_issues[:8]
        top_suggestions = all_suggestions[:8]
        strengths = all_strengths[:5]

        return ATSScoreResult(
            overall_score=overall_score,
            grade=grade,
            section_scores=section_scores,
            keyword_analysis=keyword_analysis,
            format_analysis=format_analysis,
            content_quality=content_quality,
            top_issues=top_issues,
            top_suggestions=top_suggestions,
            strengths=strengths,
            job_match_score=job_match_score,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
        )

    def _analyze_personal_info(self, resume: ResumeData) -> SectionAnalysis:
        """Analyze personal information section."""
        score = 0
        issues = []
        suggestions = []
        highlights = []

        info = resume.personal_info

        # Name (25 points)
        if info.name and len(info.name.strip()) > 1:
            score += 25
            highlights.append("Name is clearly provided")
        else:
            issues.append("Missing or incomplete name")

        # Email (25 points)
        if info.email and self.email_pattern.match(info.email):
            score += 25
            # Check for professional email
            if any(domain in info.email.lower() for domain in ['gmail.com', 'outlook.com', 'yahoo.com', 'icloud.com']):
                highlights.append("Professional email address provided")
            elif any(domain in info.email.lower() for domain in ['hotmail.com', 'aol.com']):
                suggestions.append("Consider using a more modern email provider (Gmail, Outlook)")
        else:
            issues.append("Missing or invalid email address")
            suggestions.append("Add a professional email address")

        # Phone (20 points)
        if info.phone and self.phone_pattern.search(info.phone):
            score += 20
        else:
            issues.append("Missing phone number")
            suggestions.append("Include a phone number for recruiter contact")

        # Location (10 points)
        if info.location and len(info.location.strip()) > 2:
            score += 10
        else:
            suggestions.append("Add location (City, State) for local job matching")

        # LinkedIn (10 points)
        if info.linkedin:
            score += 10
            highlights.append("LinkedIn profile included")
        else:
            suggestions.append("Add LinkedIn profile URL to increase credibility")

        # GitHub/Website (10 points) - bonus for tech roles
        if info.github or info.website:
            score += 10
            if info.github:
                highlights.append("GitHub profile showcases technical work")
            if info.website:
                highlights.append("Personal website/portfolio included")

        return SectionAnalysis(
            name="Contact Information",
            score=min(100, score),
            weight=SECTION_WEIGHTS["personal_info"],
            issues=issues,
            suggestions=suggestions,
            highlights=highlights
        )

    def _analyze_summary(self, resume: ResumeData) -> SectionAnalysis:
        """Analyze professional summary section."""
        score = 0
        issues = []
        suggestions = []
        highlights = []

        summary = resume.summary or ""

        if not summary.strip():
            issues.append("Missing professional summary")
            suggestions.append("Add a 2-3 sentence professional summary highlighting your key qualifications")
            return SectionAnalysis(
                name="Professional Summary",
                score=0,
                weight=SECTION_WEIGHTS["summary"],
                issues=issues,
                suggestions=suggestions,
                highlights=highlights
            )

        word_count = len(summary.split())

        # Length scoring (optimal: 30-75 words)
        if 30 <= word_count <= 75:
            score += 40
            highlights.append("Summary length is optimal for ATS parsing")
        elif 20 <= word_count < 30 or 75 < word_count <= 100:
            score += 30
            suggestions.append("Aim for 30-75 words in your summary")
        elif word_count < 20:
            score += 15
            issues.append("Summary is too short")
            suggestions.append("Expand your summary to include key skills and experience highlights")
        else:
            score += 20
            issues.append("Summary is too long")
            suggestions.append("Condense summary to 30-75 words for better ATS compatibility")

        # Check for keywords/skills mentioned
        has_technical_terms = bool(re.search(r'\b(engineer|developer|manager|analyst|specialist|expert|lead|senior|junior)\b', summary, re.I))
        has_years_experience = bool(re.search(r'\b(\d+)\+?\s*(years?|yrs?)\b', summary, re.I))

        if has_technical_terms:
            score += 25
        else:
            suggestions.append("Include your job title or role in the summary")

        if has_years_experience:
            score += 20
            highlights.append("Years of experience mentioned")
        else:
            suggestions.append("Mention your years of experience (e.g., '5+ years')")

        # Check for quantified achievements
        if self.quantification_pattern.search(summary):
            score += 15
            highlights.append("Summary includes quantified achievements")
        else:
            suggestions.append("Add a key achievement with numbers to your summary")

        return SectionAnalysis(
            name="Professional Summary",
            score=min(100, score),
            weight=SECTION_WEIGHTS["summary"],
            issues=issues,
            suggestions=suggestions,
            highlights=highlights
        )

    def _analyze_experience(self, resume: ResumeData) -> SectionAnalysis:
        """Analyze work experience section."""
        score = 0
        issues = []
        suggestions = []
        highlights = []

        experiences = resume.experience or []

        if not experiences:
            issues.append("No work experience listed")
            suggestions.append("Add relevant work experience, internships, or volunteer work")
            return SectionAnalysis(
                name="Work Experience",
                score=20,  # Some points for having the section
                weight=SECTION_WEIGHTS["experience"],
                issues=issues,
                suggestions=suggestions,
                highlights=highlights
            )

        # Number of experiences (optimal: 3-5)
        exp_count = len(experiences)
        if 3 <= exp_count <= 5:
            score += 20
            highlights.append(f"{exp_count} relevant positions listed")
        elif exp_count < 3:
            score += 10
            suggestions.append("Consider adding more relevant experience if available")
        else:
            score += 15
            suggestions.append("Focus on most recent 5 positions to keep resume concise")

        total_bullets = 0
        quantified_bullets = 0
        action_verb_bullets = 0

        for i, exp in enumerate(experiences):
            exp_issues = []

            # Company and position validation
            if not exp.company or not exp.position:
                exp_issues.append(f"Experience {i+1}: Missing company or position")

            # Date validation
            if not exp.start_date:
                exp_issues.append(f"Experience {i+1}: Missing start date")

            # Bullet points analysis
            bullets = exp.description or []
            total_bullets += len(bullets)

            if len(bullets) < 2:
                exp_issues.append(f"Experience {i+1}: Add more bullet points (aim for 3-5)")
            elif len(bullets) > 6:
                exp_issues.append(f"Experience {i+1}: Too many bullets - focus on top 4-5 achievements")

            for bullet in bullets:
                bullet_lower = bullet.lower()

                # Check for quantification
                if self.quantification_pattern.search(bullet):
                    quantified_bullets += 1

                # Check for action verbs
                first_word = bullet_lower.split()[0] if bullet.split() else ""
                if first_word in ALL_ACTION_VERBS:
                    action_verb_bullets += 1

                # Check for filler words
                for filler in FILLER_WORDS:
                    if filler in bullet_lower:
                        exp_issues.append(f"Avoid weak phrase: '{filler}'")
                        break

            issues.extend(exp_issues[:2])  # Limit issues per experience

        # Scoring based on bullet quality
        if total_bullets > 0:
            quant_rate = quantified_bullets / total_bullets
            action_rate = action_verb_bullets / total_bullets

            # Quantification scoring (up to 30 points)
            if quant_rate >= 0.5:
                score += 30
                highlights.append(f"{int(quant_rate*100)}% of bullets have quantified results")
            elif quant_rate >= 0.3:
                score += 20
            else:
                score += 10
                suggestions.append("Add numbers and metrics to more bullet points (aim for 50%+)")

            # Action verb scoring (up to 25 points)
            if action_rate >= 0.7:
                score += 25
                highlights.append("Strong use of action verbs")
            elif action_rate >= 0.5:
                score += 18
            else:
                score += 10
                suggestions.append("Start each bullet with a strong action verb (Led, Built, Achieved)")

            # Bullet count scoring (up to 25 points)
            avg_bullets = total_bullets / exp_count
            if 3 <= avg_bullets <= 5:
                score += 25
            elif 2 <= avg_bullets < 3 or 5 < avg_bullets <= 6:
                score += 18
            else:
                score += 10

        return SectionAnalysis(
            name="Work Experience",
            score=min(100, score),
            weight=SECTION_WEIGHTS["experience"],
            issues=issues[:5],  # Limit total issues
            suggestions=suggestions[:4],
            highlights=highlights
        )

    def _analyze_education(self, resume: ResumeData) -> SectionAnalysis:
        """Analyze education section."""
        score = 0
        issues = []
        suggestions = []
        highlights = []

        education = resume.education or []

        if not education:
            issues.append("No education listed")
            suggestions.append("Add your educational background")
            return SectionAnalysis(
                name="Education",
                score=30,  # Base score
                weight=SECTION_WEIGHTS["education"],
                issues=issues,
                suggestions=suggestions,
                highlights=highlights
            )

        # Primary education entry
        primary_edu = education[0]

        # Institution (30 points)
        if primary_edu.institution and len(primary_edu.institution) > 2:
            score += 30
        else:
            issues.append("Missing institution name")

        # Degree (30 points)
        if primary_edu.degree:
            score += 30
            degree_lower = primary_edu.degree.lower()
            if any(d in degree_lower for d in ['bachelor', 'master', 'phd', 'doctor', 'mba', 'associate']):
                highlights.append("Degree type clearly specified")
        else:
            issues.append("Missing degree information")

        # Field of study (15 points)
        if primary_edu.field:
            score += 15
        else:
            suggestions.append("Include your field of study/major")

        # Dates (15 points)
        if primary_edu.start_date or primary_edu.end_date:
            score += 15
        else:
            suggestions.append("Add graduation date or expected graduation")

        # GPA (bonus 5 points if > 3.5)
        if primary_edu.gpa:
            try:
                gpa_val = float(primary_edu.gpa.replace('/', '.').split()[0])
                if gpa_val >= 3.5:
                    score += 5
                    highlights.append(f"Strong GPA: {primary_edu.gpa}")
                elif gpa_val < 3.0:
                    suggestions.append("Consider omitting GPA below 3.0")
            except (ValueError, IndexError):
                pass

        # Highlights/honors (bonus 5 points)
        if primary_edu.highlights and len(primary_edu.highlights) > 0:
            score += 5
            highlights.append("Academic achievements/honors included")

        return SectionAnalysis(
            name="Education",
            score=min(100, score),
            weight=SECTION_WEIGHTS["education"],
            issues=issues,
            suggestions=suggestions,
            highlights=highlights
        )

    def _analyze_skills(self, resume: ResumeData) -> SectionAnalysis:
        """Analyze skills section."""
        score = 0
        issues = []
        suggestions = []
        highlights = []

        skills = resume.skills or []

        if not skills:
            issues.append("No skills section found")
            suggestions.append("Add a skills section with technical and soft skills")
            return SectionAnalysis(
                name="Skills",
                score=20,
                weight=SECTION_WEIGHTS["skills"],
                issues=issues,
                suggestions=suggestions,
                highlights=highlights
            )

        total_skills = 0
        categories_used = []

        for skill_group in skills:
            if skill_group.category:
                categories_used.append(skill_group.category)
            total_skills += len(skill_group.items or [])

        # Category organization (30 points)
        if len(categories_used) >= 3:
            score += 30
            highlights.append("Skills well-organized into categories")
        elif len(categories_used) >= 2:
            score += 20
        else:
            score += 10
            suggestions.append("Organize skills into categories (Technical, Soft Skills, Tools)")

        # Skill count (30 points)
        if 10 <= total_skills <= 25:
            score += 30
            highlights.append(f"{total_skills} relevant skills listed")
        elif 5 <= total_skills < 10:
            score += 20
            suggestions.append("Consider adding more relevant skills")
        elif total_skills > 25:
            score += 20
            suggestions.append("Focus on most relevant skills (aim for 15-20)")
        else:
            score += 10
            issues.append("Very few skills listed")

        # Technical vs soft skills balance (20 points)
        technical_keywords = ['python', 'java', 'javascript', 'sql', 'react', 'aws', 'docker',
                            'kubernetes', 'git', 'api', 'database', 'cloud', 'linux', 'agile']
        soft_keywords = ['leadership', 'communication', 'teamwork', 'problem-solving',
                        'analytical', 'project management', 'collaboration']

        all_skills_text = ' '.join(
            ' '.join(s.items or []) for s in skills
        ).lower()

        has_technical = any(kw in all_skills_text for kw in technical_keywords)
        has_soft = any(kw in all_skills_text for kw in soft_keywords)

        if has_technical and has_soft:
            score += 20
            highlights.append("Good balance of technical and soft skills")
        elif has_technical:
            score += 15
            suggestions.append("Consider adding soft skills (Leadership, Communication)")
        elif has_soft:
            score += 10
            suggestions.append("Add more technical/hard skills relevant to your field")

        # ATS-friendly formatting (20 points)
        # Check that skills aren't too long (should be concise)
        long_skills = sum(1 for s in skills for item in (s.items or []) if len(item) > 30)
        if long_skills == 0:
            score += 20
        elif long_skills <= 3:
            score += 15
        else:
            score += 10
            suggestions.append("Keep skill names concise (avoid long descriptions)")

        return SectionAnalysis(
            name="Skills",
            score=min(100, score),
            weight=SECTION_WEIGHTS["skills"],
            issues=issues,
            suggestions=suggestions,
            highlights=highlights
        )

    def _analyze_projects(self, resume: ResumeData) -> SectionAnalysis:
        """Analyze projects section."""
        score = 0
        issues = []
        suggestions = []
        highlights = []

        projects = resume.projects or []

        if not projects:
            # Projects are optional but valuable
            suggestions.append("Consider adding a projects section to showcase hands-on work")
            return SectionAnalysis(
                name="Projects",
                score=50,  # Neutral score for missing optional section
                weight=SECTION_WEIGHTS["projects"],
                issues=issues,
                suggestions=suggestions,
                highlights=highlights
            )

        # Number of projects (30 points)
        proj_count = len(projects)
        if 2 <= proj_count <= 4:
            score += 30
            highlights.append(f"{proj_count} projects showcase practical experience")
        elif proj_count == 1:
            score += 20
            suggestions.append("Add 1-2 more projects if available")
        else:
            score += 25
            suggestions.append("Focus on your top 3-4 most impressive projects")

        projects_with_tech = 0
        projects_with_description = 0
        projects_with_link = 0

        for proj in projects:
            if proj.technologies and len(proj.technologies) > 0:
                projects_with_tech += 1
            if any(
                len(text) > 20
                for text in (
                    (proj.highlights or []) + ([proj.description] if proj.description else [])
                )
                if text
            ):
                projects_with_description += 1
            if proj.link:
                projects_with_link += 1

        # Technologies listed (25 points)
        tech_rate = projects_with_tech / proj_count if proj_count > 0 else 0
        if tech_rate >= 0.8:
            score += 25
            highlights.append("Technologies clearly listed for projects")
        elif tech_rate >= 0.5:
            score += 18
        else:
            score += 10
            suggestions.append("List technologies used for each project")

        # Descriptions (25 points)
        desc_rate = projects_with_description / proj_count if proj_count > 0 else 0
        if desc_rate >= 0.8:
            score += 25
        elif desc_rate >= 0.5:
            score += 18
        else:
            score += 10
            suggestions.append("Add descriptions explaining project purpose and your role")

        # Links (20 points)
        link_rate = projects_with_link / proj_count if proj_count > 0 else 0
        if link_rate >= 0.5:
            score += 20
            highlights.append("Project links provided for verification")
        elif link_rate > 0:
            score += 12
        else:
            score += 5
            suggestions.append("Add links to live projects or GitHub repositories")

        return SectionAnalysis(
            name="Projects",
            score=min(100, score),
            weight=SECTION_WEIGHTS["projects"],
            issues=issues,
            suggestions=suggestions,
            highlights=highlights
        )

    def _analyze_keywords(self, resume: ResumeData) -> KeywordAnalysis:
        """Extract and analyze keywords from resume."""
        all_text = self._get_all_resume_text(resume)
        doc = self.nlp.process(all_text)
        terms = doc.all_terms()

        # Identify technical keywords
        tech_patterns = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node', 'django', 'flask', 'spring', 'aws', 'azure', 'gcp', 'docker',
            'kubernetes', 'terraform', 'sql', 'nosql', 'mongodb', 'postgresql',
            'redis', 'kafka', 'rabbitmq', 'graphql', 'rest', 'api', 'microservices',
            'ci', 'cd', 'devops', 'agile', 'scrum', 'git', 'linux', 'machine',
            'learning', 'data', 'analytics', 'tableau', 'excel', 'powerbi'
        ]

        technical_keywords = [kw for kw in tech_patterns if kw in terms]

        # Identify soft skill keywords
        soft_patterns = [
            'leadership', 'communication', 'teamwork', 'collaboration', 'analytical',
            'problem', 'solving', 'strategic', 'planning', 'management', 'mentoring',
            'negotiation', 'presentation', 'organization', 'adaptability', 'creativity'
        ]

        soft_skill_keywords = [kw for kw in soft_patterns if kw in terms]

        # Find action verbs used
        action_verbs_used = [v for v in ALL_ACTION_VERBS if v in doc.lemmas]

        # Common keywords that might be missing
        common_missing = []
        important_keywords = ['results', 'team', 'project', 'business', 'customer', 'client']
        for kw in important_keywords:
            if kw not in terms:
                common_missing.append(kw)

        total_tokens = len(doc.tokens)
        keyword_count = len(set(technical_keywords + soft_skill_keywords + action_verbs_used))
        keyword_density = (keyword_count / total_tokens * 100) if total_tokens > 0 else 0

        return KeywordAnalysis(
            total_keywords=keyword_count,
            technical_keywords=technical_keywords[:15],
            soft_skill_keywords=soft_skill_keywords[:10],
            action_verbs_used=action_verbs_used[:15],
            missing_common_keywords=common_missing[:5],
            keyword_density=round(keyword_density, 2)
        )

    def _analyze_format(self, resume: ResumeData) -> FormatAnalysis:
        """Analyze resume format and structure."""
        issues = []

        # Check section presence
        has_sections = {
            'personal_info': bool(resume.personal_info and resume.personal_info.name),
            'summary': bool(resume.summary),
            'experience': bool(resume.experience and len(resume.experience) > 0),
            'education': bool(resume.education and len(resume.education) > 0),
            'skills': bool(resume.skills and len(resume.skills) > 0),
        }

        has_clear_sections = sum(has_sections.values()) >= 4

        if not has_sections['experience']:
            issues.append("Missing experience section")
        if not has_sections['skills']:
            issues.append("Missing skills section")

        # Analyze bullet point consistency
        bullet_lengths = []
        for exp in (resume.experience or []):
            for bullet in (exp.description or []):
                bullet_lengths.append(len(bullet))

        bullet_consistency = 100
        if bullet_lengths:
            avg_length = sum(bullet_lengths) / len(bullet_lengths)
            variance = sum((l - avg_length) ** 2 for l in bullet_lengths) / len(bullet_lengths)
            # Lower variance = more consistent
            bullet_consistency = max(0, min(100, 100 - (variance / 100)))

            if avg_length < 30:
                issues.append("Bullet points are too short - add more detail")
            elif avg_length > 200:
                issues.append("Bullet points are too long - be more concise")

        # Estimate page count
        total_text = self._get_all_resume_text(resume)
        word_count = len(total_text.split())

        # Rough estimate: ~400-500 words per page
        estimated_pages = word_count / 450

        length_appropriate = 0.8 <= estimated_pages <= 2.2

        if estimated_pages < 0.6:
            issues.append("Resume appears too short - add more content")
        elif estimated_pages > 2.5:
            issues.append("Resume may be too long - aim for 1-2 pages")

        return FormatAnalysis(
            has_clear_sections=has_clear_sections,
            bullet_point_consistency=round(bullet_consistency, 1),
            length_appropriate=length_appropriate,
            estimated_pages=round(estimated_pages, 1),
            issues=issues
        )

    def _analyze_content_quality(self, resume: ResumeData) -> ContentQuality:
        """Analyze overall content quality."""
        issues = []

        total_bullets = 0
        quantified = 0
        action_verb_count = 0
        bullet_lengths = []
        filler_count = 0

        # Analyze experience bullets
        for exp in (resume.experience or []):
            for bullet in (exp.description or []):
                total_bullets += 1
                bullet_lengths.append(len(bullet.split()))

                if self.quantification_pattern.search(bullet):
                    quantified += 1

                first_word = bullet.lower().split()[0] if bullet.split() else ""
                if first_word in ALL_ACTION_VERBS:
                    action_verb_count += 1

                for filler in FILLER_WORDS:
                    if filler in bullet.lower():
                        filler_count += 1
                        break

        # Calculate rates
        quant_rate = (quantified / total_bullets * 100) if total_bullets > 0 else 0
        action_rate = (action_verb_count / total_bullets) if total_bullets > 0 else 0
        avg_bullet_length = (sum(bullet_lengths) / len(bullet_lengths)) if bullet_lengths else 0

        # Generate issues
        if quant_rate < 30:
            issues.append("Add more quantified achievements (numbers, percentages, metrics)")
        if action_rate < 0.5:
            issues.append("Start more bullets with strong action verbs")
        if filler_count > 2:
            issues.append(f"Remove weak phrases like 'responsible for' ({filler_count} found)")
        if avg_bullet_length < 8:
            issues.append("Bullet points lack detail - expand with specific achievements")
        elif avg_bullet_length > 35:
            issues.append("Some bullets are too long - split or condense")

        return ContentQuality(
            quantified_achievements=quantified,
            total_bullet_points=total_bullets,
            quantification_rate=round(quant_rate, 1),
            average_bullet_length=round(avg_bullet_length, 1),
            action_verb_usage_rate=round(action_rate, 2),
            filler_word_count=filler_count,
            issues=issues
        )

    def _analyze_job_match(
        self,
        resume: ResumeData,
        job_description: str
    ) -> tuple[int, list[str], list[str]]:
        """
        Analyze how well resume matches a job description.

        Returns:
            Tuple of (match_score, matched_keywords, missing_keywords)
        """
        resume_text = self._get_all_resume_text(resume)
        resume_doc = self.nlp.process(resume_text)
        jd_doc = self.nlp.process(job_description)

        resume_terms = self.nlp.filter_signal_terms(resume_doc.all_terms())
        jd_terms = self.nlp.filter_signal_terms(jd_doc.all_terms())

        weights = self.nlp.importance_weights(job_description, jd_doc.lemmas)
        total_weight = sum(weights.get(t, 1.0) for t in jd_terms) or 1.0
        matched_weight = sum(weights.get(t, 1.0) for t in jd_terms if t in resume_terms)
        coverage = matched_weight / total_weight

        # Phrase coverage gives extra credit
        phrase_matches = [p for p in jd_doc.phrases if p in resume_terms]
        phrase_bonus = min(0.2, 0.05 * len(phrase_matches))

        cosine = self.nlp.cosine_similarity(resume_doc.vector, jd_doc.vector)

        raw_score = (coverage * 0.6) + (cosine * 0.3) + phrase_bonus
        match_score = int(max(0, min(100, raw_score * 100)))

        # Determine matched/missing keywords by weight importance
        unique_jd_terms = list(dict.fromkeys(list(jd_terms) + jd_doc.phrases))
        matched = [t for t in unique_jd_terms if t in resume_terms]
        missing = [t for t in unique_jd_terms if t not in resume_terms]

        matched.sort(key=lambda t: weights.get(t, 1.0), reverse=True)
        missing.sort(key=lambda t: weights.get(t, 1.0), reverse=True)

        return match_score, matched[:20], missing[:15]

    def _get_all_resume_text(self, resume: ResumeData) -> str:
        """Concatenate all text from resume for analysis."""
        parts = []

        # Personal info
        if resume.personal_info:
            info = resume.personal_info
            parts.extend([
                info.name or "",
                info.title or "",
                info.location or "",
            ])

        # Summary
        if resume.summary:
            parts.append(resume.summary)

        # Experience
        for exp in (resume.experience or []):
            parts.extend([
                exp.company or "",
                exp.position or "",
                exp.location or "",
            ])
            parts.extend(exp.description or [])

        # Education
        for edu in (resume.education or []):
            parts.extend([
                edu.institution or "",
                edu.degree or "",
                edu.field or "",
            ])
            parts.extend(edu.highlights or [])

        # Skills
        for skill in (resume.skills or []):
            parts.append(skill.category or "")
            parts.extend(skill.items or [])

        # Projects
        for proj in (resume.projects or []):
            parts.extend([
                proj.name or "",
                proj.description or "",
            ])
            parts.extend(proj.highlights or [])
            parts.extend(proj.technologies or [])

        return " ".join(parts)

    def _score_to_grade(self, score: int) -> str:
        """Convert numeric score to letter grade."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        elif score >= 55:
            return "C-"
        elif score >= 50:
            return "D"
        else:
            return "F"


# Singleton instance
_ats_scorer: Optional[ATSScorer] = None


def get_ats_scorer() -> ATSScorer:
    """Get or create the ATS scorer singleton."""
    global _ats_scorer
    if _ats_scorer is None:
        _ats_scorer = ATSScorer()
    return _ats_scorer
