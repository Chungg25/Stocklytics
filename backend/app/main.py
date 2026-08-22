from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.endpoints import stocks, ai, trading, chat
from app.core.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # start_scheduler() # Disabled per user request
    yield
    # Shutdown
    try:
        stop_scheduler()
    except Exception:
        pass

app = FastAPI(title="Alphahubiq API", lifespan=lifespan)

# Configure CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Alphahubiq API"}

# Include Routers
app.include_router(stocks.router, prefix="/api", tags=["stocks"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
