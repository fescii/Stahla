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

# Quotes routes


@router.get("/quotes/recent", response_class=HTMLResponse)
async def read_quotes_recent(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Recent Quotes"})


@router.get("/quotes/oldest", response_class=HTMLResponse)
async def read_quotes_oldest(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Oldest Quotes"})


@router.get("/quotes/highest", response_class=HTMLResponse)
async def read_quotes_highest(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Highest Quotes"})


@router.get("/quotes/lowest", response_class=HTMLResponse)
async def read_quotes_lowest(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Lowest Quotes"})

# Location routes


@router.get("/location/recent", response_class=HTMLResponse)
async def read_location_recent(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Recent Location"})


@router.get("/location/oldest", response_class=HTMLResponse)
async def read_location_oldest(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Oldest Location"})


@router.get("/location/success", response_class=HTMLResponse)
async def read_location_success(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Successful Location"})


@router.get("/location/failed", response_class=HTMLResponse)
async def read_location_failed(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Failed Location"})


@router.get("/location/pending", response_class=HTMLResponse)
async def read_location_pending(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Pending Location"})

# HubSpot routes


@router.get("/hubspot/contacts", response_class=HTMLResponse)
async def read_hubspot_contacts(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | HubSpot Contacts"})


@router.get("/hubspot/leads", response_class=HTMLResponse)
async def read_hubspot_leads(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | HubSpot Leads"})


@router.get("/hubspot/properties", response_class=HTMLResponse)
async def read_hubspot_properties(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | HubSpot Properties"})

# Properties routes


@router.get("/properties/contact", response_class=HTMLResponse)
async def read_properties_contact(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Contact Properties"})


@router.get("/properties/lead", response_class=HTMLResponse)
async def read_properties_lead(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Lead Properties"})


@router.get("/properties/fields", response_class=HTMLResponse)
async def read_properties_fields(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Property Fields"})

# Classify routes


@router.get("/classify/recent", response_class=HTMLResponse)
async def read_classify_recent(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Recent Classification"})


@router.get("/classify/success", response_class=HTMLResponse)
async def read_classify_success(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Successful Classification"})


@router.get("/classify/failed", response_class=HTMLResponse)
async def read_classify_failed(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Failed Classification"})


@router.get("/classify/disqualified", response_class=HTMLResponse)
async def read_classify_disqualified(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Disqualified Classification"})

# Calls routes


@router.get("/calls/recent", response_class=HTMLResponse)
async def read_calls_recent(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Recent Calls"})


@router.get("/calls/success", response_class=HTMLResponse)
async def read_calls_success(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Successful Calls"})


@router.get("/calls/failed", response_class=HTMLResponse)
async def read_calls_failed(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Failed Calls"})


@router.get("/calls/oldest", response_class=HTMLResponse)
async def read_calls_oldest(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Oldest Calls"})

# Email routes


@router.get("/email/sent", response_class=HTMLResponse)
async def read_email_sent(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Sent Emails"})


@router.get("/email/failed", response_class=HTMLResponse)
async def read_email_failed(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Failed Emails"})


@router.get("/email/compose", response_class=HTMLResponse)
async def read_email_compose(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Compose Email"})


@router.get("/email/received", response_class=HTMLResponse)
async def read_email_received(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Received Emails"})

# Additional Bland routes from navigation


@router.get("/bland/calls", response_class=HTMLResponse)
async def read_bland_calls(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Bland Calls"})


@router.get("/bland/status", response_class=HTMLResponse)
async def read_bland_status(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Bland Status"})


@router.get("/bland/simulate", response_class=HTMLResponse)
async def read_bland_simulate(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Bland Simulate"})

# Legal/Static pages


@router.get("/terms", response_class=HTMLResponse)
async def read_terms(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Terms of Service"})


@router.get("/privacy", response_class=HTMLResponse)
async def read_privacy(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Privacy Policy"})


@router.get("/contact", response_class=HTMLResponse)
async def read_contact(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Contact"})


@router.get("/docs", response_class=HTMLResponse)
async def read_docs(request: Request):
  return templates.TemplateResponse("home.html", {"request": request, "url": request.url, "title": "Stahla AI SDR | Documentation"})
