# RenderCV Backend

A high-performance FastAPI backend for generating professional resumes using the [RenderCV](https://docs.rendercv.com/) engine. Features AI-powered resume parsing, ATS scoring, and multiple professional themes.

<!-- Add your API documentation screenshot here -->
![API Documentation](./docs/api-screenshot.png)
<!-- Replace with your actual screenshot path -->

## Features

- **PDF Generation** — High-quality PDFs using RenderCV's Typst-based engine
- **PNG Export** — Generate images for thumbnails or social sharing
- **Multiple Themes** — Classic, SB2Nov, ModernCV, and Engineering Resumes
- **AI Resume Parsing** — Extract structured data from PDF resumes using Google Gemini
- **ATS Score Analysis** — Comprehensive resume scoring based on real ATS systems
- **Format Conversion** — Convert frontend resume data to RenderCV YAML format
- **Docker Ready** — Optimized Dockerfile for Coolify/production deployment
- **Caching** — In-memory caching with optional Redis support

## Tech Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) with async support
- **Resume Engine:** [RenderCV](https://docs.rendercv.com/) with Typst
- **Validation:** [Pydantic 2.x](https://docs.pydantic.dev/)
- **AI/LLM:** [Google Gemini](https://ai.google.dev/) for resume parsing
- **PDF Processing:** PyMuPDF, pdfplumber, pdf2image
- **OCR:** Tesseract (pytesseract)
- **Caching:** cachetools, Redis (optional)

## Quick Start

### Local Development

1. **Create a virtual environment:**
   ```bash
   cd rendercv-backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the development server:**
   ```bash
   python run.py
   # Or: uvicorn app.main:app --reload --port 8000
   ```

5. **Open the API docs:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build directly
docker build -t rendercv-backend .
docker run -p 8000:8000 rendercv-backend
```

## API Endpoints

### Health Check
```
GET /api/health
```
Returns service status and RenderCV availability.

### Render PDF Preview
```
POST /api/render/pdf/preview
```
Generate PDF bytes for inline preview in the editor.

### Render PDF
```
POST /api/render/pdf?download=false
```
Generate PDF from resume data.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `download` | bool | false | Return as file download |

### Render PNG
```
POST /api/render/png?page=1&dpi=150&download=false
```
Generate PNG image from resume data.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number to render |
| `dpi` | int | 150 | Resolution (72-300) |
| `download` | bool | false | Return as file download |

### List Templates
```
GET /api/templates
```
Returns all available themes with descriptions and preview URLs.

### Template Preview
```
GET /api/templates/{theme_id}/preview
```
Returns PNG preview of a theme with sample data.

### Convert to YAML
```
POST /api/convert/yaml?theme=classic
```
Convert resume data to RenderCV YAML format.

### Validate Resume
```
POST /api/validate
```
Validate resume data and return warnings/suggestions.

### ATS Score Analysis
```
POST /api/ats/analyze
```
Comprehensive ATS (Applicant Tracking System) analysis including:
- Section completeness and quality scoring
- Keyword optimization analysis
- Format and structure assessment
- Content quality metrics (action verbs, quantification)
- Optional job description matching

**Request Body:**
```json
{
  "resumeData": { ... },
  "jobDescription": "Optional job posting text for matching"
}
```

**Response includes:**
- `overallScore`: 0-100 score
- `grade`: Letter grade (A+, A, B+, etc.)
- `sectionScores`: Detailed breakdown by section
- `keywordAnalysis`: Technical and soft skill keywords
- `formatAnalysis`: Structure assessment
- `contentQuality`: Bullet metrics, quantification rate
- `topIssues`: Priority issues to fix
- `topSuggestions`: Actionable improvements
- `strengths`: What the resume does well
- `jobMatchScore`: Match percentage (if JD provided)
- `matchedKeywords` / `missingKeywords`: Keyword comparison

### Parse Resume (AI)
```
POST /api/parse/resume
```
Upload a PDF resume and extract structured data using Google Gemini AI.

**Request:** `multipart/form-data` with `file` field (PDF)

**Response:**
```json
{
  "success": true,
  "data": {
    "personalInfo": { ... },
    "summary": "...",
    "experience": [ ... ],
    "education": [ ... ],
    "skills": [ ... ],
    "projects": [ ... ]
  }
}
```

### Extract Text
```
POST /api/extract/text
```
Extract raw text from an uploaded PDF file.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RENDERCV_APP_NAME` | RenderCV Backend | Application name |
| `RENDERCV_APP_VERSION` | 1.0.0 | Application version |
| `RENDERCV_DEBUG` | false | Enable debug mode |
| `RENDERCV_HOST` | 0.0.0.0 | Server host |
| `RENDERCV_PORT` | 8000 | Server port |
| `RENDERCV_CORS_ORIGINS` | ["http://localhost:3000"] | Allowed CORS origins (JSON array) |
| `RENDERCV_DEFAULT_THEME` | classic | Default resume theme |
| `RENDERCV_OUTPUT_DIR` | /tmp/rendercv_output | Temporary output directory |
| `RENDERCV_CLEANUP_AFTER_RENDER` | true | Clean up temp files after render |
| `RENDERCV_GEMINI_API_KEY` | — | Google Gemini API key (required for AI parsing) |

## Project Structure

```
rendercv-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration settings
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── resume.py           # Pydantic models
│   └── services/
│       ├── __init__.py
│       ├── rendercv_service.py # RenderCV integration
│       ├── converter.py        # Data conversion logic
│       ├── ats_scorer.py       # ATS scoring engine
│       ├── resume_parser.py    # AI resume parsing (Gemini)
│       ├── text_extractor.py   # PDF text extraction
│       ├── nlp_utils.py        # NLP utilities for ATS
│       └── cache.py            # Caching layer
├── Dockerfile
├── docker-compose.yml
├── coolify.yaml                # Coolify deployment config
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Available Themes

| Theme | Description |
|-------|-------------|
| `classic` | Clean, professional layout with traditional feel |
| `sb2nov` | Modern, minimalist design for tech roles |
| `moderncv` | Contemporary design with color accents |
| `engineeringresumes` | Optimized for technical/engineering roles |

## Deployment with Coolify

### 1. Create a New Application

In your Coolify dashboard:
1. Click "Create New Resource"
2. Select "Application"
3. Choose "Docker" as the build pack

### 2. Configure the Application

**Source:**
- Repository URL: Your Git repository URL
- Branch: `main` (or your deployment branch)
- Build Path: `rendercv-backend/`

**Build:**
- Dockerfile: `Dockerfile`
- Docker Build Arguments: (none needed)

**Environment Variables:**
```
RENDERCV_CORS_ORIGINS=["https://your-frontend-domain.com"]
RENDERCV_DEBUG=false
RENDERCV_GEMINI_API_KEY=your-gemini-api-key
```

### 3. Configure Networking

- **Port**: 8000
- **Domain**: Set your custom domain (e.g., `api.resumit.app`)
- **HTTPS**: Enable automatic SSL

### 4. Health Check

Coolify will use the configured healthcheck:
- Endpoint: `/api/health`
- Interval: 30s
- Timeout: 10s

### 5. Deploy

Click "Deploy" and wait for the build to complete.

## Frontend Integration

### TypeScript Hook Example

```typescript
// hooks/use-rendercv.ts
const API_URL = process.env.NEXT_PUBLIC_RENDERCV_API_URL || 'http://localhost:8000';

export function useRenderCV() {
  const renderPdfPreview = async (resumeData: ResumeData, theme = 'classic') => {
    const response = await fetch(`${API_URL}/api/render/pdf/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resumeData, theme }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.arrayBuffer();
  };

  const analyzeATS = async (resumeData: ResumeData, jobDescription?: string) => {
    const response = await fetch(`${API_URL}/api/ats/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resumeData, jobDescription }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  };

  const parseResume = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_URL}/api/parse/resume`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  };

  return { renderPdfPreview, analyzeATS, parseResume };
}
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black app/ --line-length 100
ruff check app/ --fix
```

### Type Checking

```bash
mypy app/
```

## License

MIT License - See LICENSE file for details.

## Related

- [RenderCV Documentation](https://docs.rendercv.com/)
- [RenderCV GitHub](https://github.com/rendercv/rendercv)
- [Typst](https://typst.app/) — The typesetting system used by RenderCV
- [Google Gemini API](https://ai.google.dev/) — AI model for resume parsing
