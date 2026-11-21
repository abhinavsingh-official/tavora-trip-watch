from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import booking, check, lab, notifications, requests, users

app = FastAPI(title="Tavora Trip Price Watch & Booking - V1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(requests.router)
app.include_router(check.router)
app.include_router(notifications.router)
app.include_router(booking.router)
app.include_router(lab.router)


@app.get("/health")
def health():
    return {"status": "ok"}
