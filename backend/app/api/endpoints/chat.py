from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json

from app.repositories.supabase_repo import supabase
from app.ai.agent import ChatAgent

router = APIRouter()
agent = ChatAgent()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    messages: List[ChatMessage]
    user_id: str = "00000000-0000-0000-0000-000000000000" # Should come from auth in production

@router.get("/sessions/{user_id}")
async def get_chat_sessions(user_id: str):
    """Fetch all chat sessions for the sidebar"""
    try:
        response = supabase.table("chat_sessions").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Fetch all messages for a specific session"""
    try:
        response = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific session and all its messages"""
    try:
        # Supabase will cascade delete messages if FK is set, but just in case we delete messages first
        supabase.table("chat_messages").delete().eq("session_id", session_id).execute()
        supabase.table("chat_sessions").delete().eq("id", session_id).execute()
        return {"status": "success", "message": "Session deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def chat_with_agent(request: ChatRequest):
    """
    Main Chat Endpoint with Streaming
    """
    try:
        session_id = request.session_id
        
        # 1. Create session if it doesn't exist
        if not session_id:
            # Generate a title from the first message
            title = request.messages[-1].content[:50] + "..."
            res = supabase.table("chat_sessions").insert({"user_id": request.user_id, "title": title}).execute()
            session_id = res.data[0]["id"]
            
        # 2. Save the incoming user message
        user_msg = request.messages[-1]
        supabase.table("chat_messages").insert({
            "session_id": session_id,
            "role": user_msg.role,
            "content": user_msg.content
        }).execute()

        # 3. Format messages for Agent
        agent_msgs = [{"role": m.role, "content": m.content} for m in request.messages]
        
        # Fetch user profile for personalization
        profile_res = supabase.table("user_profiles").select("*").eq("user_id", request.user_id).execute()
        user_profile = profile_res.data[0] if profile_res.data else None

        # 4. Stream generator
        async def event_generator():
            full_response = ""
            # Yield the session ID first so the frontend knows what session was created
            yield f"__session_id__:{session_id}\n\n"
            
            async for chunk in agent.stream_chat(agent_msgs, user_profile):
                full_response += chunk
                yield chunk
                
            # After streaming finishes, save assistant's full response to DB
            supabase.table("chat_messages").insert({
                "session_id": session_id,
                "role": "assistant",
                "content": full_response
            }).execute()
            
            # Update session timestamp
            supabase.table("chat_sessions").update({"updated_at": "now()"}).eq("id", session_id).execute()

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
