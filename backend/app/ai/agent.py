import json
import logging
from typing import List, Dict, Any, AsyncGenerator
from pathlib import Path

from app.ai.llm_client import execute_with_fallback, summarize_large_payload
from app.ai.tools import get_available_tools, execute_tool

logger = logging.getLogger(__name__)

# Load System Prompt
PROMPT_PATH = Path(__file__).parent / "prompts" / "chat_system_prompt.md"

def get_system_prompt(user_profile: Dict[str, Any] = None) -> str:
    """Loads the system prompt and injects personalization context and current date."""
    from datetime import datetime
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        base_prompt = f.read()
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    date_context = f"\n\n## CURRENT CONTEXT\n- Today's Date: {current_date}\n- Ensure all references to current or future years align with this date (e.g., FY {datetime.now().year})."
    
    if user_profile:
        risk = user_profile.get("risk_tolerance", "moderate")
        sectors = ", ".join(user_profile.get("preferred_sectors", []))
        personalization = f"\n\n## USER PROFILE\n- Risk Tolerance: {risk.upper()}\n- Preferred Sectors: {sectors}\nAdapt your risk warnings and language to suit this profile."
        return base_prompt + date_context + personalization
        
    return base_prompt + date_context

class ChatAgent:
    def __init__(self):
        self.tools_schema = get_available_tools()

    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        user_profile: Dict[str, Any] = None
    ) -> AsyncGenerator[str, None]:
        """
        Main agent loop with streaming response.
        Handles Tool Calls automatically.
        """
        system_prompt = get_system_prompt(user_profile)
        
        # Ensure system prompt is the first message
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_prompt})
            
        # Prune chat history to avoid token limits (keep system prompt + last 4 messages)
        # Frontend only sends user/assistant roles, so slicing is safe from breaking tool call chains.
        if len(messages) > 5:
            messages = [messages[0]] + messages[-4:]

        # Core Loop for Tool Execution
        MAX_ITERATIONS = 15
        for i in range(MAX_ITERATIONS):
            # If on the last iteration, remove tools so it's forced to respond
            current_tools = self.tools_schema if i < MAX_ITERATIONS - 1 else None
            
            if i == MAX_ITERATIONS - 1:
                messages.append({
                    "role": "system",
                    "content": "You have reached the maximum number of tool calls. You must now synthesize the information you have and answer the user."
                })

            # 1. Send to LLM
            tool_calls = []
            final_content = ""
            
            try:
                response_chunks = execute_with_fallback(
                    messages=messages,
                    tools=current_tools,
                    stream=True
                )

                # Since Groq/Zhipu returns tool calls in chunks if streamed, we need to collect them
                for chunk in response_chunks:
                    delta = chunk.choices[0].delta
                    
                    # Check for tool call
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tc_chunk in delta.tool_calls:
                            if len(tool_calls) <= tc_chunk.index:
                                tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                            
                            if tc_chunk.id:
                                tool_calls[tc_chunk.index]["id"] = tc_chunk.id
                            if tc_chunk.function.name:
                                tool_calls[tc_chunk.index]["function"]["name"] = tc_chunk.function.name
                            if tc_chunk.function.arguments:
                                tool_calls[tc_chunk.index]["function"]["arguments"] += tc_chunk.function.arguments
                    
                    # Yield text content to client
                    if delta.content:
                        final_content += delta.content
                        yield delta.content
            except Exception as e:
                error_msg = str(e)
                if "413" in error_msg or "rate limit" in error_msg.lower():
                    friendly_error = "Hệ thống AI đang quá tải khối lượng dữ liệu (Rate Limit). Vui lòng thu hẹp phạm vi câu hỏi hoặc đợi 1 phút rồi thử lại."
                elif "402" in error_msg:
                    friendly_error = "Tài khoản API Key đã hết hạn mức (No Credit). Vui lòng nạp thêm để tiếp tục."
                else:
                    friendly_error = f"Lỗi hệ thống: {error_msg}"
                yield f"\n\n__ERROR__:{friendly_error}\n\n"
                break

            import re

            # 2. Custom XML Parser for Hallucinated Tool Calls (DeepSeek DSML/XML compatibility)
            if not tool_calls and ("<invoke" in final_content or "<WEBSEARCH" in final_content):
                # Pattern 1: <invoke name="web_search"> <parameter name="query">...</parameter> </invoke>
                invoke_pattern = r'<\s*invoke\s+name=["\'](.*?)["\']\s*>([\s\S]*?)<\s*/\s*invoke\s*>'
                invokes = re.findall(invoke_pattern, final_content)
                for name, body in invokes:
                    if name in ["web_search", "web_search_with_citations", "search", "Bash"]:
                        param_pattern = r'<\s*parameter\s+name=["\'](?:query|command)["\'][^>]*>([\s\S]*?)<\s*/\s*parameter\s*>'
                        match = re.search(param_pattern, body)
                        if match:
                            query = match.group(1).strip()
                            tool_calls.append({
                                "id": f"call_xml_{len(tool_calls)}",
                                "type": "function",
                                "function": {
                                    "name": "web_search_with_citations",
                                    "arguments": json.dumps({"query": query})
                                }
                            })
                            
                # Pattern 2: <WEBSEARCH> <QUERY>...</QUERY> </WEBSEARCH>
                websearch_pattern = r'<\s*WEBSEARCH\s*>[\s\S]*?<\s*QUERY\s*>([\s\S]*?)<\s*/\s*QUERY\s*>[\s\S]*?<\s*/\s*WEBSEARCH\s*>'
                websearches = re.findall(websearch_pattern, final_content)
                for query in websearches:
                    tool_calls.append({
                        "id": f"call_xml_ws_{len(tool_calls)}",
                        "type": "function",
                        "function": {
                            "name": "web_search_with_citations",
                            "arguments": json.dumps({"query": query.strip()})
                        }
                    })

            # 2.5 If no tool calls (JSON or XML), we are done!
            if not tool_calls:
                # Add assistant message to history
                messages.append({"role": "assistant", "content": final_content})
                break
                
            # 3. Handle Tool Calls
            # Add assistant's tool call request to messages
            messages.append({
                "role": "assistant",
                "content": final_content if final_content else None,
                "tool_calls": tool_calls
            })

            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                try:
                    kwargs = json.loads(tool_call["function"]["arguments"])
                    logger.info(f"Agent calling tool: {func_name} with {kwargs}")
                    
                    # Execute the tool silently without yielding to the chat stream
                    # The frontend will just show the "Analyzing..." bouncing dots.
                    result = execute_tool(func_name, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Error executing {func_name}: {e}")
                    result = {"error": str(e)}

                # Truncate or Summarize tool results to prevent Groq Rate Limit (8000 TPM limit)
                result_str = json.dumps(result, ensure_ascii=False)
                if len(result_str) > 2500:
                    logger.info(f"Payload too large ({len(result_str)} chars). Routing to Summarizer LLM...")
                    result_str = summarize_large_payload(result_str)

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": func_name,
                    "content": result_str
                })
            
            # The loop will naturally continue and send the new messages (with tool results) back to LLM
