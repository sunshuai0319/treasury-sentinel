import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import execution_configured, get_keeperhub_client, get_repository, router
from app.config import get_settings
from app.workers.execution_monitor import execution_recovery_loop


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.keeperhub_poll_enabled and execution_configured(settings):
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            execution_recovery_loop(
                get_repository(),
                get_keeperhub_client().get_status,
                settings.keeperhub_poll_interval_seconds,
                stop_event,
            )
        )
        try:
            yield
        finally:
            stop_event.set()
            await task
    else:
        yield


app = FastAPI(title="Treasury Sentinel API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")
