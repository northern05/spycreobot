import logging
import traceback

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import http_exception_handler
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.models import db_helper, Base
from app.api import router as router_v1
from app.core.config import config
from utils.extra import check_payments

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Started lifespan")
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(check_payments, "cron", minute='*/1')
    # scheduler.start()
    async with db_helper.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    print("End lifespan")


app = FastAPI(
    lifespan=lifespan,
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}},
    openapi_url="/docs.json",
    docs_url="/docs"
)


class LogRequestBodyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log request details
        logging.info(f"Incoming Request: {request.method} {request.url}")
        logging.info(f"Request Headers: {request.headers}")

        # Check if there's a request body and if it's JSON
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Read the request body
                body = await request.body()
                logging.info(f"Request Body: {body.decode('utf-8')}")

                # If you specifically want to parse JSON and log it,
                # you might need to handle the stream carefully.
                # However, for debugging 422s, the raw body is often enough.
                # If you need to access the parsed JSON later in the request,
                # you'll need to re-create the stream or store it.
                # For logging, just reading it is fine.

            except Exception as e:
                logging.error(f"Error reading request body: {e}")

        response = await call_next(request)
        logging.info(f"Response Status: {response.status_code}")
        return response


app.add_middleware(LogRequestBodyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=router_v1, prefix=config.api_v1_prefix)


@app.exception_handler(HTTPException)
async def exception_handler(request: Request, exc: HTTPException):
    logger.info("Handling http exception")
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def exception_handler_2(request: Request, exc: Exception):
    msg = f"URL: {request.url}\n\n"
    msg += traceback.format_exc()

    # await tg_bot.send_message(msg)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content="Server error!"
    )


async def format_request(request: Request):
    msg = f"URL: {request.url}\n"

    body = await request.body()
    msg += f"Body: {body.decode()}"

    return msg


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# add formatter to handlers
if len(logger.handlers) > 0:
    logger.handlers[0].setLevel(logging.DEBUG)
    logger.handlers[0].setFormatter(formatter)
else:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


