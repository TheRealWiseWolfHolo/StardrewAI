"""FastAPI backend for the Stardew Valley AI chat agent."""

import logging
import time
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from config.settings import settings
from src.agent.stardew_agent import AgentMode, StardewAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Stardew Valley AI Assistant", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

templates = Jinja2Templates(directory="src/frontend/templates")
agent: Optional[StardewAgent] = None

# --- Pydantic Models ---
class PlayerContext(BaseModel):
    year: Optional[int] = 1
    season: Optional[str] = "Spring"
    day: Optional[int] = 1

class ChatMessage(BaseModel):
    message: str
    mode: Optional[str] = None
    context: Optional[PlayerContext] = None


class RichChatResponse(BaseModel):
    text: Optional[str] = None
    image_url: Optional[str] = None
    table: Optional[Dict] = None
    checklist: Optional[Dict] = None
    source_url: Optional[str] = None
    mode: str
    timestamp: float = Field(default_factory=time.time)

class ModeChangeRequest(BaseModel):
    mode: str

class AgentStatus(BaseModel):
    mode: str
    is_ready: bool

# --- Agent Lifecycle ---
@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup."""
    global agent
    try:
        logger.info("Initializing Stardew Valley agent...")
        agent = StardewAgent(mode=AgentMode.HINTS)
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)
        agent = None

# --- API Routes ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status", response_model=AgentStatus)
async def get_status():
    """Get the current agent status."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return AgentStatus(mode=agent.mode.value, is_ready=True)

@app.post("/api/chat", response_model=RichChatResponse)
async def chat(message: ChatMessage):
    """Process a chat message and return a structured response."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        if message.mode:
            try:
                new_mode = AgentMode(message.mode.lower())
                if agent.mode != new_mode:
                    agent.set_mode(new_mode)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid mode specified.")
        
        # Agent's chat method now returns a dictionary
        response_data = agent.chat(
            message=message.message,
            context=message.context.dict() if message.context else None
        )
        
        return RichChatResponse(
            **response_data,
            mode=agent.mode.value
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing message.")

@app.post("/api/mode")
async def change_mode(request: ModeChangeRequest):
    """Change the agent's operating mode."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        new_mode = AgentMode(request.mode.lower())
        agent.set_mode(new_mode)
        return {"success": True, "mode": new_mode.value}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mode specified.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )