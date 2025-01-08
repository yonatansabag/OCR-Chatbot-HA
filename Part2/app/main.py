from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routes import router
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Format logs with timestamp
    handlers=[
        logging.FileHandler("chatbot.log"),  # Save logs to a file
        logging.StreamHandler()  # Print logs to the console
    ]
)

logger = logging.getLogger(__name__)  

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application is starting...")
    yield
    # Shutdown
    logger.info("Application is shutting down...")

# Creating the app
app = FastAPI(
    title="Medical Chatbot",
    description="A chatbot for medical services in Israel",
    version="1.0.0",
    lifespan=lifespan
)

# Include the router with endpoints
app.include_router(router)

# root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Medical Chatbot API"}
