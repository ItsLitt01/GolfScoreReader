
from fastapi import FastAPI

from app import config
from app.routes import router

app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION)
app.include_router(router)
