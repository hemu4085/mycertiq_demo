# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.search_cme import router as search_cme_router
from app.api.routes.vector_search import router as vector_search_router
from app.api.routes.ask_cme import router as ask_cme_router  # 👈 NEW

app = FastAPI(
    title="MyCertiQ Demo API",
    version="0.1.0",
)

# ---------------------------------------------------------
# CORS (tweak origins as needed)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------
@app.get("/", tags=["health"])
def read_root():
    return {"status": "ok", "service": "mycertiq_demo"}

# ---------------------------------------------------------
# Existing CME routes
# ---------------------------------------------------------
app.include_router(search_cme_router, prefix="/search", tags=["search"])

# ---------------------------------------------------------
# Vector search routes
# ---------------------------------------------------------
app.include_router(vector_search_router, prefix="/vector", tags=["vector"])

# ---------------------------------------------------------
# NEW: Human-like CME Query API
# ---------------------------------------------------------
app.include_router(ask_cme_router, prefix="/ask", tags=["ask"])
