import os

def get_assessment_prompt_template(mode: str) -> str:
    file_map = {
        "checklist": "investment-checklist.md",
        "research": "investment-research.md",
        "team": "investment-team.md",
        "tradingagents": "trading-agents.md",
        "tradingagents_fast": "trading-agents-fast.md"
    }
    file_name = file_map.get(mode, "investment-checklist.md")
    
    # Climb up to root/skill
    current_dir = os.path.dirname(__file__)
    prompt_path = os.path.join(current_dir, "..", "..", "..", "skill", file_name)
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        return f"Could not load skill file {file_name}: {e}"
        
    return template

def build_assessment_prompt(ticker: str, mode: str, context: str = "") -> str:
    template = get_assessment_prompt_template(mode)
    
    # Replace arguments
    full_prompt = template.replace("$ARGUMENTS", ticker)
    if context:
        full_prompt = full_prompt.replace("$CONTEXT", context)
        
    full_prompt += f"\n\n[FINAL SYSTEM DIRECTIVE]\n1. You MUST write your ENTIRE response in ENGLISH, regardless of the user's prompt. Translate all your analysis, headers, and bullet points into ENGLISH. This is a strict requirement.\n2. IMPORTANT: You MUST use your own native web_search tool to find the absolute latest real-time financial data, news and events about this company to supplement your analysis. ALWAYS cite your sources as links at the end of your report."
    
    return full_prompt
