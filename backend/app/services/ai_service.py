import os
from dotenv import load_dotenv
# from zhipuai import ZhipuAI
from openai import OpenAI

load_dotenv()

def generate_ai_analysis(tickers, prompt):
    api_key = os.getenv("API_KEY")
    if not api_key:
        return (
            "**Error: Zhipu API Key Missing**\n\n"
            "To use the GLM 5.1 AI Analysis feature, please set the `ZHIPU_API_KEY` environment variable on the backend server. "
            "You can add it to a `.env` file or export it directly."
        )

    if not tickers:
        return "Please select at least one stock to analyze."
    client = OpenAI(
        base_url="https://zenmux.ai/api/v1",
        api_key=api_key,
    )
    
    # Construct the final prompt by injecting the tickers
    tickers_str = ", ".join(tickers)
    full_prompt = (
        f"You are an expert financial analyst. Please analyze the following stocks: {tickers_str}.\n\n"
        f"User Query: {prompt}\n\n"
        "Please provide a comprehensive, markdown-formatted response."
    )

    try:
        response = client.chat.completions.create(
            model="z-ai/glm-4.7-flash-free",
            messages=[
                {"role": "user", "content": full_prompt}
            ],
            tools=[{"type": "web_search", "web_search": {"enable": True}}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"**Error during AI Analysis:**\n\n```\n{str(e)}\n```"
