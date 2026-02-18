import uvicorn
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from cachetools import TTLCache

from core.config import PORT, WEBHOOK_SECRET
from core.logger import setup_logger

import run_group_bot
import run_ai_bot
import run_crypto_bot
import run_support_bot
import run_admin_bot

logger = setup_logger("GATEWAY")

webhook_rate = TTLCache(maxsize=500000, ttl=5)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

MAX_REQUEST_SIZE = 1_000_000  # 1MB


async def rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    
    webhook_rate[client_ip] = webhook_rate.get(client_ip, 0) + 1
    if "/webhook/" in request.url.path:
        return webhook_rate[client_ip] <= 200
    return webhook_rate[client_ip] <= 50


async def check_request_size(request: Request):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        return False
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 MONOLITH STARTING")
    if not WEBHOOK_SECRET:
        logger.critical("⚠️ WEBHOOK_SECRET is not set! Webhooks are insecure.")

    async def safe_start(name, func):
        try:
            await func()
            logger.info(f"✅ {name} started")
        except Exception as e:
            logger.error(f"{name} failed to start: {e}")

    await asyncio.gather(
        safe_start("GROUP", run_group_bot.start_service),
        safe_start("AI", run_ai_bot.start_service),
        safe_start("CRYPTO", run_crypto_bot.start_service),
        safe_start("SUPPORT", run_support_bot.start_service),
        safe_start("ADMIN", run_admin_bot.start_service),
    )
    yield
    logger.info("🛑 MONOLITH SHUTDOWN")
    try:
        await asyncio.wait_for(
            asyncio.gather(
                run_group_bot.stop_service(),
                run_ai_bot.stop_service(),
                run_crypto_bot.stop_service(),
                run_support_bot.stop_service(),
                run_admin_bot.stop_service(),
                return_exceptions=True,
            ),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        logger.error("⚠️ Force closing: a service refused to shut down in time.")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def global_protection(request: Request, call_next):
    if not await check_request_size(request):
        return JSONResponse({"error": "Payload too large. Max 1MB."}, status_code=413)
    
    if not await rate_limit(request):
        return JSONResponse({"error": "Rate Limit Exceeded."}, status_code=429)
    
    response = await call_next(request)
    
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        {"error": "An internal error occurred"},
        status_code=500
    )


app.include_router(run_group_bot.router)
app.include_router(run_ai_bot.router)
app.include_router(run_crypto_bot.router)
app.include_router(run_support_bot.router)
app.include_router(run_admin_bot.router)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "system": "Project Monolith"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)