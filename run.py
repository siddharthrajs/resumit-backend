#!/usr/bin/env python3
"""
Development server runner for RenderCV Backend.
Use this for local development and testing.
"""
import os
import sys


def main():
    # Add the project directory to the path
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_dir)
    
    # Import uvicorn
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install uvicorn[standard]")
        sys.exit(1)
    
    # Check for RenderCV
    try:
        import rendercv
        print(f"✓ RenderCV version: {getattr(rendercv, '__version__', 'unknown')}")
    except ImportError:
        print("⚠ Warning: RenderCV not installed. Run: pip install 'rendercv[full]'")
        print("  Some features will not work without RenderCV.")
    
    # Get configuration from environment
    host = os.getenv("RENDERCV_HOST", "0.0.0.0")
    port = int(os.getenv("RENDERCV_PORT", "8000"))
    debug = os.getenv("RENDERCV_DEBUG", "true").lower() == "true"
    
    print(f"\n🚀 Starting RenderCV Backend")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Debug: {debug}")
    print(f"\n📚 API Documentation: http://localhost:{port}/docs")
    print(f"📖 ReDoc: http://localhost:{port}/redoc")
    print(f"❤️  Health Check: http://localhost:{port}/api/health\n")
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info",
    )


if __name__ == "__main__":
    main()

