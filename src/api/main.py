"""FastAPI backend for the Stardew Valley AI chat agent."""

import logging
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config.settings import settings
from src.agent.stardew_agent import AgentMode, StardewAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Stardew Valley AI Assistant",
    description="An AI-powered chat agent to help with Stardew Valley gameplay",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="src/frontend/templates")

# Global agent instance
agent: Optional[StardewAgent] = None


# Pydantic models
class ChatMessage(BaseModel):
    message: str
    mode: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    mode: str
    timestamp: float


class ModeChangeRequest(BaseModel):
    mode: str


class AgentStatus(BaseModel):
    mode: str
    mode_info: Dict
    is_ready: bool


# Initialize agent
@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup."""
    global agent
    try:
        logger.info("Initializing Stardew Valley agent...")
        agent = StardewAgent(mode=AgentMode.HINTS)
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}")
        agent = None


# API Routes
@app.get("/")
async def home(request: Request):
    """Serve the main chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def get_status() -> AgentStatus:
    """Get the current agent status and mode information."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return AgentStatus(
        mode=agent.mode.value,
        mode_info=agent.get_mode_info(),
        is_ready=True
    )


@app.post("/api/chat")
async def chat(message: ChatMessage) -> ChatResponse:
    """Process a chat message and return the agent's response."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Change mode if requested
        if message.mode:
            try:
                new_mode = AgentMode(message.mode.lower())
                if agent.mode != new_mode:
                    agent.set_mode(new_mode)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid mode: {message.mode}. Use 'hints' or 'walkthrough'"
                )
        
        # Get response from agent
        response = agent.chat(message.message)
        
        return ChatResponse(
            response=response,
            mode=agent.mode.value,
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing message")


@app.post("/api/mode")
async def change_mode(request: ModeChangeRequest) -> Dict:
    """Change the agent's operating mode."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        new_mode = AgentMode(request.mode.lower())
        agent.set_mode(new_mode)
        
        return {
            "success": True,
            "mode": agent.mode.value,
            "mode_info": agent.get_mode_info()
        }
        
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid mode: {request.mode}. Use 'hints' or 'walkthrough'"
        )
    except Exception as e:
        logger.error(f"Error changing mode: {str(e)}")
        raise HTTPException(status_code=500, detail="Error changing mode")


@app.get("/api/history")
async def get_conversation_history() -> List[Dict]:
    """Get the current conversation history."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        messages = agent.get_conversation_history()
        history = []
        
        for msg in messages:
            history.append({
                "type": msg.__class__.__name__,
                "content": msg.content,
                "timestamp": getattr(msg, 'timestamp', None)
            })
        
        return history
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving history")


@app.post("/api/clear")
async def clear_conversation() -> Dict:
    """Clear the conversation history."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        agent.clear_memory()
        return {"success": True, "message": "Conversation history cleared"}
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Error clearing conversation")


@app.get("/api/modes")
async def get_available_modes() -> Dict:
    """Get information about available agent modes."""
    return {
        "modes": {
            "hints": {
                "name": "Hints Mode",
                "description": "Provides subtle guidance and hints without spoilers",
                "style": "Encouraging nudges that let you discover solutions",
                "response_length": "Concise (under 200 words)",
                "spoiler_protection": "High - avoids revealing solutions directly"
            },
            "walkthrough": {
                "name": "Full Walkthrough Mode",
                "description": "Provides detailed step-by-step instructions", 
                "style": "Comprehensive guides with complete solutions",
                "response_length": "Detailed (comprehensive explanations)",
                "spoiler_protection": "Low - provides complete information"
            }
        },
        "default_mode": "hints"
    }


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_ready": agent is not None,
        "version": "1.0.0"
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return templates.TemplateResponse(
        "error.html", 
        {"request": request, "error": "Page not found", "status_code": 404},
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Internal server error", "status_code": 500},
        status_code=500
    )


if __name__ == "__main__":
    import time
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )
