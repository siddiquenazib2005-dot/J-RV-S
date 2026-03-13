"""
J-RV-S Orchestrator — Core Brain Router
By Nazib Siddique
"""

import re

# Tool intent keywords
INTENT_MAP = {
    "weather": ["weather", "temperature", "rain", "forecast", "humidity", "mausam"],
    "news": ["news", "headline", "breaking", "current events", "latest", "khabar"],
    "search": ["search", "find", "look up", "google", "who is", "what is", "khojo", "batao"],
    "wikipedia": ["wikipedia", "wiki", "define", "meaning", "history of"],
    "calculator": ["calculate", "math", "solve", "+", "-", "*", "/", "=", "percent", "calculate"],
    "currency": ["currency", "convert", "usd", "inr", "dollar", "rupee", "euro", "rate"],
    "pdf": ["pdf", "document", "file", "read this", "analyze this", "summarize this file"],
    "image": ["image", "photo", "picture", "analyze image", "what is in this", "screenshot"],
    "code": ["code", "program", "function", "debug", "error", "script", "python", "javascript", "fix this"],
    "translate": ["translate", "translation", "in hindi", "in english", "anuvad", "language"],
    "summarize": ["summarize", "summary", "tldr", "brief", "short", "saaransh"],
    "stock": ["stock", "share price", "market", "sensex", "nifty", "crypto", "bitcoin"],
    "memory": ["remember", "recall", "my name", "what did i say", "yaad", "history"],
    "task": ["task", "todo", "remind", "add task", "my tasks", "kaam"],
    "notes": ["note", "write down", "save this", "note karo", "notes"],
    "chat": []  # default fallback
}

def detect_intent(user_message: str) -> str:
    """Detect what tool/intent the user wants."""
    msg = user_message.lower()
    
    for intent, keywords in INTENT_MAP.items():
        if intent == "chat":
            continue
        for keyword in keywords:
            if keyword in msg:
                return intent
    
    return "chat"  # Default: normal AI conversation

def build_system_prompt(intent: str, user_name: str = "Boss", memories: list = []) -> str:
    """Build dynamic system prompt based on intent."""
    
    base = f"""You are J-RV-S (Just a Rather Very Intelligent System), an advanced AI assistant built by Nazib Siddique.
You are talking to {user_name}.
You are intelligent, helpful, direct, and slightly witty — like JARVIS from Iron Man.
Always respond in the same language the user uses (Hindi or English or Hinglish).
Keep responses clear, structured, and useful.
"""

    memory_block = ""
    if memories:
        memory_block = "\n\nUser Memory:\n" + "\n".join([f"- {m}" for m in memories[-10:]])

    intent_prompts = {
        "weather": base + "\nUser asked about weather. If tool result is provided, present it clearly with emojis.",
        "news": base + "\nUser wants news. Present headlines clearly, numbered list format.",
        "search": base + "\nUser wants to search something. Summarize findings clearly.",
        "wikipedia": base + "\nUser wants Wikipedia info. Give a clear, educational summary.",
        "calculator": base + "\nUser wants math solved. Show step-by-step solution.",
        "currency": base + "\nUser wants currency conversion. Show current rate and converted amount.",
        "pdf": base + "\nUser uploaded a PDF/file. Analyze and summarize the content clearly.",
        "image": base + "\nUser uploaded an image. Describe and analyze it in detail.",
        "code": base + "\nUser needs coding help. Write clean, commented, working code. Explain what it does.",
        "translate": base + "\nUser wants translation. Provide accurate translation with context if needed.",
        "summarize": base + "\nUser wants a summary. Be concise and capture key points only.",
        "stock": base + "\nUser asked about stocks/crypto. Present data clearly with context.",
        "memory": base + "\nUser is asking about their memory/history. Use the memory block provided.",
        "task": base + "\nUser is managing tasks. Be organized and confirm actions clearly.",
        "notes": base + "\nUser wants to save/retrieve notes. Confirm clearly.",
        "chat": base + "\nEngage in natural, intelligent conversation. Be helpful, witty, and insightful."
    }

    return intent_prompts.get(intent, intent_prompts["chat"]) + memory_block

def format_tool_result(intent: str, result: dict) -> str:
    """Format tool results into a readable string for AI context."""
    if not result:
        return ""
    
    if intent == "weather":
        return f"""
Weather Data:
City: {result.get('city', 'N/A')}
Temperature: {result.get('temp', 'N/A')}°C
Condition: {result.get('description', 'N/A')}
Humidity: {result.get('humidity', 'N/A')}%
Wind: {result.get('wind', 'N/A')} km/h
"""
    elif intent == "search":
        snippets = result.get('results', [])
        formatted = "\n".join([f"- {r.get('title','')}: {r.get('snippet','')}" for r in snippets[:3]])
        return f"Search Results:\n{formatted}"
    
    elif intent == "wikipedia":
        return f"Wikipedia Summary:\n{result.get('summary', '')}"
    
    elif intent == "news":
        articles = result.get('articles', [])
        formatted = "\n".join([f"{i+1}. {a.get('title','')}" for i, a in enumerate(articles[:5])])
        return f"Latest News:\n{formatted}"
    
    elif intent == "currency":
        return f"Currency: 1 {result.get('from','')} = {result.get('rate','')} {result.get('to','')}"
    
    elif intent == "stock":
        return f"Stock: {result.get('symbol','')} | Price: {result.get('price','')} | Change: {result.get('change','')}"
    
    return str(result)

def orchestrate(user_message: str, user_name: str = "Boss", memories: list = [], tool_result: dict = None) -> dict:
    """
    Main orchestration function.
    Returns: { intent, system_prompt, tool_context }
    """
    intent = detect_intent(user_message)
    system_prompt = build_system_prompt(intent, user_name, memories)
    tool_context = ""
    
    if tool_result:
        tool_context = format_tool_result(intent, tool_result)
    
    return {
        "intent": intent,
        "system_prompt": system_prompt,
        "tool_context": tool_context
    }
