# RenderCV Backend

A high-performance FastAPI backend for generating professional resumes using the [RenderCV](https://docs.rendercv.com/) engine. Designed for fast PDF generation with multiple professional themes.

## Features

- **PDF Generation**: Create high-quality PDFs using RenderCV's Typst-based engine
- **PNG Export**: Generate PNG images for thumbnails or social sharing
- **Multiple Themes**: Support for Classic, SB2Nov, ModernCV, and Engineering Resumes themes
- **Format Conversion**: Convert frontend resume data to RenderCV YAML format
- **Docker Ready**: Optimized Dockerfile for Coolify deployment
- **CORS Configured**: Ready for frontend integration

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

3. **Run the development server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. **Open the API docs:**
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

Query Parameters:
- `download`: If `true`, returns PDF as file download

### Render PNG
```
POST /api/render/png?page=1&dpi=150&download=false
```
Generate PNG image from resume data.

Query Parameters:
- `page`: Page number (default: 1)
- `dpi`: Resolution 72-300 (default: 150)
- `download`: If `true`, returns PNG as file download

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

Click "Deploy" and wait for the build to complete. The API will be available at your configured domain.

## Available Themes

| Theme | Description |
|-------|-------------|
| `classic` | Clean, professional layout with traditional feel |
| `sb2nov` | Modern, minimalist design for tech roles |
| `moderncv` | Contemporary design with color accents |
| `engineeringresumes` | Optimized for technical roles |

## Frontend Integration

### TypeScript Hook Example

```typescript
// hooks/use-rendercv.ts
import { useState, useCallback } from 'react';

const API_URL = process.env.NEXT_PUBLIC_RENDERCV_API_URL || 'http://localhost:8000';

export function useRenderCV() {
  const [pdfData, setPdfData] = useState<ArrayBuffer | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const renderPdfPreview = useCallback(async (resumeData: ResumeData, theme = 'classic') => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/render/pdf/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resumeData, theme }),
      });
      
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
      }

      const buffer = await response.arrayBuffer();
      setPdfData(buffer);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Render failed');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const downloadPdf = useCallback(async (resumeData: ResumeData, theme = 'classic') => {
    const response = await fetch(`${API_URL}/api/render/pdf?download=true`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resumeData, theme }),
    });
    
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${resumeData.personalInfo.name}_Resume.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  return { pdfData, isLoading, error, renderPdfPreview, downloadPdf };
}
```

## Development

### Project Structure

```
rendercv-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # API endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── resume.py        # Pydantic models
│   └── services/
│       ├── __init__.py
│       ├── converter.py     # Data conversion logic
│       └── rendercv_service.py  # RenderCV integration
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black app/
ruff check app/ --fix
```

## License

MIT License - See LICENSE file for details.

## Related

- [RenderCV Documentation](https://docs.rendercv.com/)
- [RenderCV GitHub](https://github.com/rendercv/rendercv)
- [Typst](https://typst.app/) - The typesetting system used by RenderCV

# resumit-backend
