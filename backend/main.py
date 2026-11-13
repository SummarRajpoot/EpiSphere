from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, AsyncSessionLocal
from routes import regions, weather, prediction, hospitals, alerts, chatbot

import sys
import asyncio
import selectors
import logging

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from services.data_fetcher import fetch_and_update_all
    async with AsyncSessionLocal() as session:
        try:
            await fetch_and_update_all(session)
        except Exception as e:
            logger.warning(f"Initial data fetch failed: {e}. DB may be empty.")

    from services.scheduler import start_scheduler
    start_scheduler()
    yield

app = FastAPI(title="OutbreakIQ API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def catch_exceptions_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.exception("Unhandled exception occurred during request")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

app.include_router(regions.router)
app.include_router(weather.router)
app.include_router(prediction.router)
app.include_router(hospitals.router)
app.include_router(alerts.router)
app.include_router(chatbot.router)

@app.get("/")
async def root():
    return {
        "status": "success",
        "message": "OutbreakIQ API is running.",
        "endpoints": {
            "GET /api/regions": "Dashboard regions and stats",
            "GET /api/alerts": "Outbreak alerts",
            "GET /api/hospitals": "Hospital finder",
            "POST /api/chatbot": "AI assistant",
            "GET /api/weather/{city}": "Weather and air quality",
            "GET /api/predict": "Disease prediction",
        },
    }

if __name__ == "__main__":
    import uvicorn

    async def _serve():
        config = uvicorn.Config(app, host="0.0.0.0", port=7860, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    def _loop_factory():
        if sys.platform == "win32":
            return asyncio.SelectorEventLoop(selectors.SelectSelector())
        return asyncio.new_event_loop()

    asyncio.run(_serve(), loop_factory=_loop_factory)
