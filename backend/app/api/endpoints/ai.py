from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.ai_service import generate_ai_analysis, generate_ai_assessment, parse_ai_intent
from app.ai.llm_client import get_active_key_status

router = APIRouter()

class AIAnalysisRequest(BaseModel):
    tickers: list[str]
    prompt: str

@router.post("/analysis")
def run_ai_analysis(req: AIAnalysisRequest):
    try:
        result = generate_ai_analysis(req.tickers, req.prompt)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class AIAssessmentRequest(BaseModel):
    ticker: str
    mode: str
    user_prompt: str = ""

@router.post("/assessment")
def run_ai_assessment(req: AIAssessmentRequest):
    return StreamingResponse(
        generate_ai_assessment(req.ticker, req.mode, req.user_prompt),
        media_type="text/event-stream"
    )

class AIIntentRequest(BaseModel):
    prompt: str

@router.post("/intent")
def run_ai_intent(req: AIIntentRequest):
    try:
        result = parse_ai_intent(req.prompt)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/status")
def get_ai_status():
    try:
        status = get_active_key_status()
        return {"status": "success", "active_key": status}
    except Exception as e:
        return {"status": "error", "message": str(e)}
