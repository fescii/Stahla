# filepath: app/api/v1/endpoints/mongo/__init__.py
from fastapi import APIRouter
from .quotes import router as quotes_router
from .calls import router as calls_router
from .classify import router as classify_router
from .location import router as location_router
from .emails import router as emails_router

# Create the main mongo router
mongo_router = APIRouter()

# Include all mongo collection routers
mongo_router.include_router(quotes_router, tags=["Mongo Quotes"])
mongo_router.include_router(calls_router, tags=["Mongo Calls"])
mongo_router.include_router(classify_router, tags=["Mongo Classify"])
mongo_router.include_router(location_router, tags=["Mongo Location"])
mongo_router.include_router(emails_router, tags=["Mongo Emails"])
