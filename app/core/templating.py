# app/core/templating.py
from fastapi.templating import Jinja2Templates

TEMPLATES_DIRECTORY = "app/templates"

templates = Jinja2Templates(directory=TEMPLATES_DIRECTORY)
