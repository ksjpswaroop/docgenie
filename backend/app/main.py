from fastapi import FastAPI

from .api.jobs import router as jobs_router
from .api.sse import router as sse_router

app = FastAPI()

# Include routers
app.include_router(jobs_router)
app.include_router(sse_router)
