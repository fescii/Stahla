# app/api/v1/endpoints/documentation.py

import os
import markdown
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import logfire

# Create a router for documentation endpoints
router = APIRouter()

# Calculate path relative to this file (documentation.py)
# Go up three levels from app/api/v1/endpoints/ to the project root, then into docs/
_ENDPOINT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_ENDPOINT_DIR))))
DOCS_DIR = os.path.join(_PROJECT_ROOT, "docs")

logfire.info(f"Documentation router serving docs from calculated path: {DOCS_DIR}")

@router.get("/docs/{filename:path}", response_class=HTMLResponse, tags=["Documentation"])
async def get_static_doc(filename: str):
    """
    Serves Markdown documentation files from the project's /docs directory as HTML.
    Allows accessing files with or without the .md extension.
    Example: /api/v1/docs/features will serve docs/features.md
    """
    # Construct the full path to the potential markdown file
    filepath = os.path.join(DOCS_DIR, filename)

    # Ensure the requested path is within the DOCS_DIR to prevent directory traversal
    abs_docs_dir = os.path.realpath(DOCS_DIR)
    # Resolve the potential file path first before checking existence
    potential_filepath_md = filepath if filename.endswith('.md') else filepath + '.md'
    abs_filepath = os.path.realpath(potential_filepath_md)

    if not abs_filepath.startswith(abs_docs_dir):
        logfire.warning(f"Attempted directory traversal: {filename}")
        raise HTTPException(status_code=404, detail="File not found")

    # Check if the file exists (with or without .md)
    actual_filepath = None
    if os.path.isfile(filepath) and filepath.endswith('.md'):
        actual_filepath = filepath
    elif os.path.isfile(potential_filepath_md):
         actual_filepath = potential_filepath_md
    else:
        logfire.warning(f"Static doc file not found for request: {filename} (Checked: {filepath}, {potential_filepath_md})")
        raise HTTPException(status_code=404, detail="File not found")

    # Ensure we are only serving markdown files (redundant check due to logic above, but safe)
    if not actual_filepath.endswith('.md'):
        raise HTTPException(status_code=403, detail="File type not allowed")

    try:
        with open(actual_filepath, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Convert Markdown to HTML
        html_content = markdown.markdown(
            md_content,
            extensions=['markdown.extensions.fenced_code', 'markdown.extensions.tables', 'pymdownx.superfences']
        )

        # Basic HTML structure
        html_page = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{os.path.basename(actual_filepath)}</title>
            <style>
                body {{ font-family: sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: auto; }}
                pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                code {{ font-family: monospace; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                /* Basic styling */
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        return HTMLResponse(content=html_page)

    except Exception as e:
        logfire.error(f"Error serving doc file {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

