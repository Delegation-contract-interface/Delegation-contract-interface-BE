import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import contracts, sessions

app = FastAPI(title="Delegation Contract API")

_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(contracts.router)
app.include_router(sessions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
