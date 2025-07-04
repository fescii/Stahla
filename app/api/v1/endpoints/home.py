# app/api/v1/endpoints/home.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.templating import templates

router = APIRouter()

# /


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Dashboard"})

# /status


@router.get("/status", response_class=HTMLResponse)
async def read_status(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Status"})

# /overview


@router.get("/overview", response_class=HTMLResponse)
async def read_overview(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Overview"})

# /hubspot


@router.get("/hubspot", response_class=HTMLResponse)
async def read_hubspot(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | HubSpot"})

# /cache


@router.get("/cache", response_class=HTMLResponse)
async def read_cache(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Cache"})

# /cache/clear


@router.get("/cache/clear", response_class=HTMLResponse)
async def read_cache_clear(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Clear Cache"})

# /users/all


@router.get("/users/all", response_class=HTMLResponse)
async def read_users_all(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | All Users"})

# /users/active


@router.get("/users/active", response_class=HTMLResponse)
async def read_users_active(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Active Users"})

# /users/inactive


@router.get("/users/inactive", response_class=HTMLResponse)
async def read_users_inactive(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Inactive Users"})

# /users/add


@router.get("/users/add", response_class=HTMLResponse)
async def read_users_add(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Add User"})

# /users/profile


@router.get("/users/profile", response_class=HTMLResponse)
async def read_users_profile(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | User Profile"})

# /pricing/location


@router.get("/pricing/location", response_class=HTMLResponse)
async def read_pricing_location(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Pricing Location"})

# /pricing/quote


@router.get("/pricing/quote", response_class=HTMLResponse)
async def read_pricing_quote(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Pricing Quote"})

# /pricing/locations


@router.get("/pricing/locations", response_class=HTMLResponse)
async def read_pricing_locations(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Pricing Locations"})

# /pricing/quotes


@router.get("/pricing/quotes", response_class=HTMLResponse)
async def read_pricing_quotes(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Pricing Quotes"})

# /bland/all


@router.get("/bland/all", response_class=HTMLResponse)
async def read_bland_all(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Bland All"})

# /bland/failed


@router.get("/bland/failed", response_class=HTMLResponse)
async def read_bland_failed(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Bland Failed"})

# /bland/recent


@router.get("/bland/recent", response_class=HTMLResponse)
async def read_bland_recent(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Bland Recent"})

# /sheet/config


@router.get("/sheet/config", response_class=HTMLResponse)
async def read_sheet_config(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Sheet Config"})

# /sheet/branches


@router.get("/sheet/branches", response_class=HTMLResponse)
async def read_sheet_branches(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Sheet Branches"})

# /sheet/generators


@router.get("/sheet/generators", response_class=HTMLResponse)
async def read_sheet_generators(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Sheet Generators"})

# /sheet/products


@router.get("/sheet/products", response_class=HTMLResponse)
async def read_sheet_products(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Sheet Products"})


# /sheet/states
@router.get("/sheet/states", response_class=HTMLResponse)
async def read_sheet_states(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Sheet States"})

# /themes


@router.get("/themes", response_class=HTMLResponse)
async def read_themes(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Themes"})

# /updates


@router.get("/updates", response_class=HTMLResponse)
async def read_updates(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Updates"})

# /docs/api


@router.get("/docs/api", response_class=HTMLResponse)
async def read_docs_api(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | API Documentation"})

# /docs/code


@router.get("/docs/code", response_class=HTMLResponse)
async def read_docs_code(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Code Documentation"})

# /docs/features


@router.get("/docs/features", response_class=HTMLResponse)
async def read_docs_features(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Features"})

# /docs/faq


@router.get("/docs/faq", response_class=HTMLResponse)
async def read_docs_faq(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | FAQ"})

# /docs/services


@router.get("/docs/services", response_class=HTMLResponse)
async def read_docs_services(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Services"})

# /docs/webhooks


@router.get("/docs/webhooks", response_class=HTMLResponse)
async def read_docs_webhooks(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Webhooks"})

# /docs/hubspot


@router.get("/docs/hubspot", response_class=HTMLResponse)
async def read_docs_hubspot(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | HubSpot"})

# /docs/marvin


@router.get("/docs/marvin", response_class=HTMLResponse)
async def read_docs_marvin(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Marvin"})
