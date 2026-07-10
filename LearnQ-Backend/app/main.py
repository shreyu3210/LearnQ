from fastapi import FastAPI
from app.api.routes import videos, users
from app.db import database, models
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title="Lecture Processor API",
    description="An API to transcribe, summarize, and analyze lecture videos."
)

models.Base.metadata.create_all(bind=database.engine)


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# Include the routes from the videos.py file with a URL prefix
app.include_router(videos.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1/users") 
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Lecture Processor API!"}

