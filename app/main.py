import asyncio
import hashlib
import hmac
import json
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routes import dashboard, webhook
from app.services.review_store import ReviewStore

load_dotenv()

store = ReviewStore()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = store
    yield

app = FastAPI(
    title="AI Code Reviewer",
    description="GitHub PR review bot powered by Claude",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(dashboard.router)

app.mount("/static", StaticFiles(directory="dashboard"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
   with open("index.html", encoding="utf-8") as f:
    return f.read()

@app.get("/health")
async def health():
    return {"status": "ok", "service": "AI Code Reviewer"}
