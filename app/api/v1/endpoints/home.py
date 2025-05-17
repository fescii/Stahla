# app/api/v1/endpoints/home.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
  return templates.TemplateResponse("home.html", {"request": request})
