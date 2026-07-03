from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import risk, chat, advisory

app = FastAPI(title="APAC City Resilience Copilot")

# CORS: allows the React UI (served from file://, localhost, or Firebase Hosting
# after deploy) to call this API from a different origin. allow_origins=["*"] is
# fine for a hackathon demo with no auth; tighten to your actual UI domain once
# you have a fixed deploy URL, since "*" + credentials is a real trust-boundary
# gap in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(risk.router)
app.include_router(chat.router)
app.include_router(advisory.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}