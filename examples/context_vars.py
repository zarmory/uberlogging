import asyncio
from contextvars import ContextVar

import structlog

import uberlogging

ctx_request_id: ContextVar = ContextVar("request_id")
logger = structlog.get_logger(__name__)


async def handle_request(request_id: str) -> None:
    ctx_request_id.set(request_id)
    logger.info("Handling request")  # Will produce "Handling request    request_id=<request_id>


async def server():
    logger.info("Main server handling two requests")
    t1 = asyncio.create_task(handle_request("Zf1glE"))
    t2 = asyncio.create_task(handle_request("YcEf73"))
    await asyncio.wait((t1, t2))
    logger.info("Main server done")


if __name__ == "__main__":
    uberlogging.configure(contextvars=(ctx_request_id,))
    asyncio.run(server())
