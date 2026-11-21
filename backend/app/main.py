import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import booking, check, lab, notifications, requests, users
from app.routers.booking import bookings_router
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The real 5-minute automatic monitoring cycle (Sec. 06) - starts with
    # the app, stops with it. See app/scheduler.py.
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Tavora Trip Price Watch & Booking - V2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(requests.router)
app.include_router(check.router)
app.include_router(notifications.router)
app.include_router(booking.router)
app.include_router(bookings_router)
app.include_router(lab.router)


@app.get("/health")
def health():
    return {"status": "ok"}
