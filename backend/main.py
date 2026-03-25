"""CashDabba – FastAPI app entry point."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT
from database.connection import engine, Base
from database.seed import seed_database
from routers import auth, dashboard, actions, insights, news, entries, ocr, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed on startup."""
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(
    title="CashDabba API",
    description="Cash flow management for small food businesses in India",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – allow all origins for hackathon demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers under /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(actions.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(news.router, prefix="/api/v1")
app.include_router(entries.router, prefix="/api/v1")
app.include_router(ocr.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "CashDabba API is running", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
