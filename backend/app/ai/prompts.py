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
        
    full_prompt += f"\n\n[FINAL SYSTEM DIRECTIVE]\n1. MẶC ĐỊNH sử dụng công cụ `TeamCreate` để tạo ra một đội 4 chuyên gia (Kinh doanh, Tài chính, Ngành, Rủi ro). Sau đó dùng `TaskCreate` để phân công họ phân tích các dữ liệu kỹ thuật và tin tức đã được cung cấp ở trên.\n2. Tùy ý sử dụng thêm `web_search_with_citations` nếu bạn cần đào sâu thêm thông tin. KHÔNG sử dụng các định dạng công cụ nội bộ (như XML hay Bash) mà hãy dùng chuẩn Tool Call của hệ thống."
    
    return full_prompt
